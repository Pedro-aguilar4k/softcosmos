SET TERM ^ ;

create or alter procedure SP_CARDEX_GERA_INVENTARIO (
    PLOJA integer,
    PDATA timestamp)
returns (
    LOJA integer,
    DATA timestamp,
    CODPRODUTO integer,
    DESCRICAO varchar(150),
    QUANTIDADE double precision,
    UNIDADE varchar(3),
    VALORUNITARIO double precision,
    TIPOPRECO varchar(30))
as
declare variable VTIPOPRECO integer;
declare variable VDECIMAIS integer;
begin
  LOJA = PLOJA;

  DATA = dateadd(day, 1, cast(PDATA as date));
  DATA = dateadd(second, -1, DATA);
  while (exists (select * from INVENTARIO
                 where LOJA = :LOJA
                 and DATA = :DATA)) do
    DATA = dateadd(second, -1, DATA);

  select first 1 VALORPADRAOINVENTARIO from CONFIGURACAO
  into :VTIPOPRECO;
  if (VTIPOPRECO = 1) then
    TIPOPRECO = 'Custo contábil ponderado';
  else
  if (VTIPOPRECO = 2) then
    TIPOPRECO = 'Preço de aquisição';
  else
    TIPOPRECO = 'CMV cadastro de produto';

  select first 1 coalesce(CPCASASDECIMAISPRECO,2) from EMPRESA
  where CODLOJA = :LOJA
  into :VDECIMAIS;
  if (VDECIMAIS < 2) then
    VDECIMAIS = 2;

  for select P.CODPRODUTO, P.DESCRICAO, P.CODEMBALAGEM,
             case :VTIPOPRECO
               when 1 then avg(round(coalesce(E.CUSTOPONDERADO,0),:VDECIMAIS))
               when 2 then avg(round(coalesce(P.PRECOAQUISICAO,0),:VDECIMAIS))
               else avg(round(coalesce(P.CMV,0),:VDECIMAIS))
               end as VALORUNITARIO
      from PRODUTOS P
      left join ESTOQUE E on E.LOJA = :LOJA and E.CODPRODUTO = P.CODPRODUTO
      where (P.INATIVO is null or P.INATIVO <> 'T')
      and P.SITTRIB <> '0S0'
      group by P.CODPRODUTO, P.DESCRICAO, P.CODEMBALAGEM
      order by P.CODPRODUTO
      into :CODPRODUTO, :DESCRICAO, :UNIDADE, :VALORUNITARIO do
  begin
    select first 1 SALDO from SP_CARDEX_1(:LOJA, :CODPRODUTO, '', 'INVENTARIO', 1, 0)
    where DATA < dateadd(day, 1, cast(:DATA as date))
    order by DATA desc
    into :QUANTIDADE;

    suspend;
  end
end^

SET TERM ; ^