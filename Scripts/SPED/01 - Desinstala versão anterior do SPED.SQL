execute block
as
declare variable NAME varchar(100);
begin
  delete from EXPORTACOESARQUIVOS
  where CODIGOARQUIVO in (10000, 10001);
  delete from EXPORTACOESFORMATACOES
  where CODIGOARQUIVO in (10000, 10001);
  delete from EXPORTACOESPARAMETROS
  where CODIGOARQUIVO in (10000, 10001);
  delete from EXPORTACOESREGISTROS
  where CODIGOARQUIVO in (10000, 10001);

  for select trim(RDB$PROCEDURE_NAME)
      from RDB$PROCEDURES
      where RDB$PROCEDURE_NAME like 'EFD_%'
      into NAME
  do
  begin
    execute statement 'drop procedure ' || NAME;
  end

  for select trim(RDB$RELATION_NAME)
      from RDB$RELATIONS
      where RDB$RELATION_NAME = 'CONTADORES' or RDB$RELATION_NAME like 'TB_ECF%'
      into NAME
  do
  begin
    execute statement 'drop table ' || NAME;
  end
end