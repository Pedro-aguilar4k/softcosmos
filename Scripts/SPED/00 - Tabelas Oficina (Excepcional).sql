/******************************************************************************/
/***                                 Tables                                 ***/
/******************************************************************************/



CREATE TABLE ITEMSSERV (
    LOJA            INTEGER NOT NULL,
    CODOS           INTEGER NOT NULL,
    NUMITEM         INTEGER NOT NULL,
    CODSERVICO      INTEGER,
    DESCRICAO       VARCHAR(60),
    SITTRIB         VARCHAR(2),
    ISS             DOUBLE PRECISION,
    HORAS           DOUBLE PRECISION,
    DESCONTO        DOUBLE PRECISION,
    PRECO           DOUBLE PRECISION,
    CODGRUPO        VARCHAR(5),
    EXPORT          VARCHAR(1),
    DESCONTOPER     DOUBLE PRECISION,
    CODFUNCIONARIO  VARCHAR(14),
    QUANTIDADE      DOUBLE PRECISION,
    LOTEEXPORT      INTEGER,
    TRIGGERATIVA    VARCHAR(1),
    CODCLFISCAL     VARCHAR(3),
    SITTRIBECF      VARCHAR(3),
    ISSECF          DOUBLE PRECISION,
    CFOP            VARCHAR(4),
    UNIDADE         VARCHAR(6)
);


CREATE TABLE OS (
    LOJA                    INTEGER NOT NULL,
    CODOS                   INTEGER NOT NULL,
    DATA                    TIMESTAMP,
    HORA                    TIMESTAMP,
    PLACA                   VARCHAR(15),
    CGC                     VARCHAR(14),
    KM                      DOUBLE PRECISION,
    OPERADOR                VARCHAR(20),
    OPERADORCAIXA           VARCHAR(20),
    STATUS                  INTEGER,
    DATASTATUS              TIMESTAMP,
    TOTALPRODUTOS           DOUBLE PRECISION,
    TOTALSERVICOS           DOUBLE PRECISION,
    CUPOMFISCAL             INTEGER,
    CFOP                    VARCHAR(4),
    TOTALPAGO               DOUBLE PRECISION,
    EF                      DOUBLE PRECISION,
    TOTALOS                 DOUBLE PRECISION,
    ENCARGOSFINANCEIROS     DOUBLE PRECISION,
    CODCONDPAG              INTEGER,
    OPERADORLIBERACAO       VARCHAR(20),
    TOTAL                   DOUBLE PRECISION,
    NUMEROPECAS             DOUBLE PRECISION,
    DESCONTORPECAS          DOUBLE PRECISION,
    DESCONTOPPECAS          DOUBLE PRECISION,
    DESCONTORSERVICOS       DOUBLE PRECISION,
    DESCONTOPSERVICOS       DOUBLE PRECISION,
    NATUREZAOPERACAO        VARCHAR(250),
    DATACANCELAMENTO        TIMESTAMP,
    OPERADORCANCELAMENTO    VARCHAR(20),
    MOTIVOCANCELAMENTO      VARCHAR(100),
    NUMERONOTA              VARCHAR(20),
    OBS                     VARCHAR(100),
    OBSPEDIDO               VARCHAR(250),
    DADOSENTREGA            VARCHAR(250),
    EXPORT                  VARCHAR(1),
    LOTEEXPORT              INTEGER,
    TIPOFRETE               VARCHAR(3),
    VALORIPI                DOUBLE PRECISION,
    VALORSUBTRIB            DOUBLE PRECISION,
    ISENTAS                 DOUBLE PRECISION,
    OUTRAS                  DOUBLE PRECISION,
    REQUISICAOESTOQUE       VARCHAR(1),
    TRIGGERATIVA            VARCHAR(1),
    SEPARADOR               VARCHAR(30),
    CODENDERECO             INTEGER,
    INSCESTADUAL            VARCHAR(18),
    CEI                     VARCHAR(20),
    ENDERECO                VARCHAR(60),
    BAIRRO                  VARCHAR(30),
    CIDADE                  VARCHAR(30),
    UF                      VARCHAR(2),
    CEP                     VARCHAR(10),
    DDD                     VARCHAR(4),
    FONE                    VARCHAR(15),
    CELULAR                 VARCHAR(15),
    CODSITFISCAL            VARCHAR(3),
    LIBERACAO               VARCHAR(20),
    MOTIVOLIBERACAO         VARCHAR(255),
    MOTIVODESCONFIRMACAO    VARCHAR(255),
    PRAZOMEDIO              DOUBLE PRECISION,
    LC                      DOUBLE PRECISION,
    LU                      DOUBLE PRECISION,
    DV                      DOUBLE PRECISION,
    PD                      TIMESTAMP,
    SITUACAO                VARCHAR(50),
    CUSTOFOB                DOUBLE PRECISION,
    VALORICMS               DOUBLE PRECISION,
    ENCARGOSTRIBUTARIOS     DOUBLE PRECISION,
    PREMIO                  DOUBLE PRECISION,
    TOTALLIQUIDOPRODUTOS    DOUBLE PRECISION,
    GM                      DOUBLE PRECISION,
    GMMIN                   DOUBLE PRECISION,
    BASECALCICMSST          DOUBLE PRECISION,
    ICMSST                  DOUBLE PRECISION,
    FLAGICMSSTMANUAL        VARCHAR(1),
    OUTRASDESPESAS          DOUBLE PRECISION,
    CODVENDEDOR             INTEGER,
    ORCAMENTOTROCA          INTEGER,
    TOTALTROCA              DOUBLE PRECISION,
    CODCIDADEIBGE           INTEGER,
    CGCCONSUMIDOR           VARCHAR(14),
    FINALIDADENFE           INTEGER,
    CAIXA                   INTEGER,
    CODGRUPOPRECO           INTEGER,
    CODTRANSF               INTEGER,
    ORCAMENTODEVOLVIDO      INTEGER,
    TRUNCARPRECOVENDA       VARCHAR(1),
    OPTANTESIMPLESNACIONAL  VARCHAR(1)
);


CREATE TABLE SERVICOS (
    CODSERVICO      INTEGER NOT NULL,
    DESCRICAO       VARCHAR(100),
    HORAS           DOUBLE PRECISION,
    SITTRIB         VARCHAR(2),
    ISS             DOUBLE PRECISION,
    EXPORT          VARCHAR(1),
    LOTEEXPORT      INTEGER,
    CODAPLICACAO    INTEGER,
    COMISSAO        DOUBLE PRECISION,
    VALOR           DOUBLE PRECISION,
    CODCLFISCAL     VARCHAR(3),
    CODREFERENCIA   VARCHAR(40),
    CUSTO           DOUBLE PRECISION,
    CODEMBALAGEM    VARCHAR(3),
    CODCENTROCUSTO  VARCHAR(15),
    OBS             VARCHAR(255)
);




/******************************************************************************/
/***                              Primary Keys                              ***/
/******************************************************************************/

ALTER TABLE ITEMSSERV ADD CONSTRAINT PK_ITEMSSERV_1 PRIMARY KEY (LOJA, CODOS, NUMITEM);
ALTER TABLE OS ADD CONSTRAINT PK_OS_1 PRIMARY KEY (LOJA, CODOS);
ALTER TABLE SERVICOS ADD CONSTRAINT PK_SERVICOS_1 PRIMARY KEY (CODSERVICO);
