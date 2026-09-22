SET TERM ^ ;

create or alter procedure SP_BAIXAS_ORIGEM_R (
    P_SEQUENCIAL varchar(30),
    P_VALOR double precision,
    P_LOJA integer,
    P_CODORCAMENTO integer,
    P_PARCELA integer,
    P_DATA timestamp)
returns (
    SEQUENCIAL varchar(30),
    LOJARECEB integer,
    DATARECEB timestamp,
    ITEM integer,
    VALOR double precision,
    QUITACAOLOJA integer,
    QUITACAOCODORCAMENTO integer,
    QUITACAOPARCELA integer,
    QUITACAODATA timestamp,
    BAIXALOJA integer,
    BAIXACODORCAMENTO integer,
    BAIXAPARCELA integer,
    BAIXADATA timestamp)
as
declare variable V_TOTAL double precision;
declare variable V_SEQUENCIAL integer;
declare variable V_VALOR double precision;
begin
  select sum(B.VALOR)
  from RECEBBAIXA B
  where B.QUITACAOLOJA = :P_LOJA and
        B.QUITACAOCODORCAMENTO = :P_CODORCAMENTO and
        B.QUITACAOPARCELA = :P_PARCELA and
        B.QUITACAODATA = :P_DATA and
        B.STATUS = 1
  into V_TOTAL;
  V_SEQUENCIAL = 0;
  if (V_TOTAL is not null) then
  begin
    for select B.LOJARECEB, B.DATARECEB, B.ITEM, B.VALOR, B.QUITACAOLOJA, B.QUITACAOCODORCAMENTO, B.QUITACAOPARCELA,
               B.QUITACAODATA, B.BAIXALOJA, B.BAIXACODORCAMENTO, B.BAIXAPARCELA, B.BAIXADATA
        from RECEBBAIXA B
        where B.QUITACAOLOJA = :P_LOJA and
              B.QUITACAOCODORCAMENTO = :P_CODORCAMENTO and
              B.QUITACAOPARCELA = :P_PARCELA and
              B.QUITACAODATA = :P_DATA and
              B.STATUS = 1
        into LOJARECEB, DATARECEB, ITEM, VALOR, QUITACAOLOJA, QUITACAOCODORCAMENTO, QUITACAOPARCELA, QUITACAODATA,
             BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
    do
    begin
      V_SEQUENCIAL = V_SEQUENCIAL + 1;
      SEQUENCIAL = P_SEQUENCIAL || '.' || lpad(V_SEQUENCIAL, 3, '0');
      VALOR = trunc(P_VALOR * VALOR / V_TOTAL * 100 + 0.5) / 100;
      V_VALOR = VALOR;
      suspend;
      for select SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, QUITACAOLOJA, QUITACAOCODORCAMENTO, QUITACAOPARCELA,
                 QUITACAODATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
          from SP_BAIXAS_ORIGEM_R(:SEQUENCIAL, :V_VALOR, :BAIXALOJA, :BAIXACODORCAMENTO, :BAIXAPARCELA, :BAIXADATA)
          into SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, QUITACAOLOJA, QUITACAOCODORCAMENTO, QUITACAOPARCELA,
               QUITACAODATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
      do
      begin
        suspend;
      end
    end
  end
end^

create or alter procedure SP_BAIXAS_ORIGEM_S (
    P_DATAINICIO timestamp,
    P_DATAFIM timestamp)
returns (
    QUITACAO integer,
    SEQUENCIAL varchar(30),
    LOJARECEB integer,
    DATARECEB timestamp,
    ITEM integer,
    VALOR double precision,
    RECEBLOJA integer,
    RECEBCODORCAMENTO integer,
    RECEBPARCELA integer,
    RECEBDATA timestamp,
    QUITACAOLOJA integer,
    QUITACAOCODORCAMENTO integer,
    QUITACAOPARCELA integer,
    QUITACAODATA timestamp,
    BAIXALOJA integer,
    BAIXACODORCAMENTO integer,
    BAIXAPARCELA integer,
    BAIXADATA timestamp)
as
declare variable V_VALOR double precision;
begin
  QUITACAO = 0;
  for select B.LOJARECEB, B.DATARECEB, B.ITEM, B.VALOR, B.QUITACAOLOJA, B.QUITACAOCODORCAMENTO, B.QUITACAOPARCELA,
             B.QUITACAODATA, B.QUITACAOLOJA, B.QUITACAOCODORCAMENTO, B.QUITACAOPARCELA, B.QUITACAODATA, B.BAIXALOJA,
             B.BAIXACODORCAMENTO, B.BAIXAPARCELA, B.BAIXADATA
      from RECEBBAIXA B
      join RECEBIMENTOS R on R.LOJA = B.QUITACAOLOJA and R.CODORCAMENTO = B.QUITACAOCODORCAMENTO and R.PARCELA = B.QUITACAOPARCELA and R.DATA = B.QUITACAODATA
      where B.DATARECEB >= :P_DATAINICIO and
            B.DATARECEB < :P_DATAFIM and
            B.STATUS = 1 and
            R.DATARECEBIMENTO is not null and
            R.STATUS = 1 and
            not exists(select *
                       from RECEBBAIXA B2
                       where B2.BAIXALOJA = B.QUITACAOLOJA and
                             B2.BAIXACODORCAMENTO = B.QUITACAOCODORCAMENTO and
                             B2.BAIXAPARCELA = B.QUITACAOPARCELA and
                             B2.BAIXADATA = B.QUITACAODATA and
                             B2.STATUS = 1)
      into LOJARECEB, DATARECEB, ITEM, VALOR, RECEBLOJA, RECEBCODORCAMENTO, RECEBPARCELA, RECEBDATA, QUITACAOLOJA,
           QUITACAOCODORCAMENTO, QUITACAOPARCELA, QUITACAODATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
  do
  begin
    QUITACAO = QUITACAO + 1;
    SEQUENCIAL = '001';
    V_VALOR = VALOR;
    suspend;
    for select SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, QUITACAOLOJA, QUITACAOCODORCAMENTO, QUITACAOPARCELA,
               QUITACAODATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
        from SP_BAIXAS_ORIGEM_R(:SEQUENCIAL, :V_VALOR, :BAIXALOJA, :BAIXACODORCAMENTO, :BAIXAPARCELA, :BAIXADATA)
        into SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, QUITACAOLOJA, QUITACAOCODORCAMENTO, QUITACAOPARCELA,
             QUITACAODATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
    do
    begin
      suspend;
    end
  end
end^

create or alter procedure SP_BAIXAS_ORIGEM (
    P_DATAINICIO timestamp,
    P_DATAFIM timestamp)
returns (
    QUITACAO integer,
    SEQUENCIAL varchar(30),
    LOJARECEB integer,
    DATARECEB timestamp,
    ITEM integer,
    VALOR double precision,
    RECEBLOJA integer,
    RECEBCODORCAMENTO integer,
    RECEBPARCELA integer,
    RECEBDATA timestamp,
    BAIXALOJA integer,
    BAIXACODORCAMENTO integer,
    BAIXAPARCELA integer,
    BAIXADATA timestamp)
as
declare variable V_QUITACAO_OLD integer;
declare variable V_SEQUENCIAL_LNG integer;
begin
  P_DATAINICIO = cast(P_DATAINICIO as date);
  P_DATAFIM = cast(P_DATAFIM as date) + 1;
  V_QUITACAO_OLD = 0;
  for select QUITACAO, SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, RECEBLOJA, RECEBCODORCAMENTO, RECEBPARCELA,
             RECEBDATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
      from SP_BAIXAS_ORIGEM_S(:P_DATAINICIO, :P_DATAFIM)
      order by QUITACAO asc, SEQUENCIAL desc
      into QUITACAO, SEQUENCIAL, LOJARECEB, DATARECEB, ITEM, VALOR, RECEBLOJA, RECEBCODORCAMENTO, RECEBPARCELA,
           RECEBDATA, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
  do
  begin
    if (V_QUITACAO_OLD <> QUITACAO) then
    begin
      V_QUITACAO_OLD = QUITACAO;
      V_SEQUENCIAL_LNG = 0;
    end
    if (V_SEQUENCIAL_LNG <= char_length(SEQUENCIAL)) then
    begin
      V_SEQUENCIAL_LNG = char_length(SEQUENCIAL);
      suspend;
    end
  end
  QUITACAO = null;
  SEQUENCIAL = null;
  ITEM = null;
  RECEBLOJA = null;
  RECEBCODORCAMENTO = null;
  RECEBPARCELA = null;
  RECEBDATA = null;
  for select R.LOJA, R.DATARECEBIMENTO, R.VALOR, R.LOJA, R.CODORCAMENTO, R.PARCELA, R.DATA
      from RECEBIMENTOS R
      where R.DATARECEBIMENTO >= :P_DATAINICIO and
            R.DATARECEBIMENTO < :P_DATAFIM and
            R.STATUS = 1 and
            not exists(select *
                       from RECEBBAIXA B
                       where ((B.QUITACAOLOJA = R.LOJA and
                             B.QUITACAOCODORCAMENTO = R.CODORCAMENTO and
                             B.QUITACAOPARCELA = R.PARCELA and
                             B.QUITACAODATA = R.DATA) or (B.BAIXALOJA = R.LOJA and
                             B.BAIXACODORCAMENTO = R.CODORCAMENTO and
                             B.BAIXAPARCELA = R.PARCELA and
                             B.BAIXADATA = R.DATA)) and
                             B.STATUS = 1)
      into LOJARECEB, DATARECEB, VALOR, BAIXALOJA, BAIXACODORCAMENTO, BAIXAPARCELA, BAIXADATA
  do
  begin
    suspend;
  end
end^

SET TERM ; ^