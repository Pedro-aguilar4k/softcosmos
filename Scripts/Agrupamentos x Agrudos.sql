with AGRUPAMENTO
as (select O.LOJA, O.CODORCAMENTO as CODAGRUPAMENTO, O.DATASTATUS as DATAAGRUPAMENTO, I.CODPRODUTO, sum(I.QUANTIDADE * I.PRECO * (1 -
           case
             when O.TOTALPRODUTOS = 0 then 0
             else case
                    when O.DESCONTOR <= 0 then O.DESCONTOR / O.TOTALPRODUTOS
                    else O.DESCONTOR / (O.TOTALPRODUTOS - coalesce(O.TOTALPRODUTOSPROMOCAO, 0)) * case
                                                                                                    when I.DATAPROMOCAO is null then 1
                                                                                                    else 0
                                                                                                  end
                  end
           end +
           case
             when O.TOTALPRODUTOS = 0 then 0
             else case
                    when O.ENCARGOSFINANCEIROS >= 0 then O.ENCARGOSFINANCEIROS / O.TOTALPRODUTOS
                    else O.ENCARGOSFINANCEIROS / (O.TOTALPRODUTOS - coalesce(O.TOTALPRODUTOSPROMOCAO, 0)) * case
                                                                                                              when I.DATAPROMOCAO is null then 1
                                                                                                              else 0
                                                                                                            end
                  end
           end +
           case
             when O.TOTALPRODUTOS = 0 then 0
             else coalesce(O.OUTRASDESPESAS, 0) / O.TOTALPRODUTOS
           end)) / sum(I.QUANTIDADE) as PRECOAGRUPAMENTO
    from ORCAMENTOS O
    join ITEMSPROD I on I.LOJA = O.LOJA and I.CODORCAMENTO = O.CODORCAMENTO
    where O.MOTIVOCANCELAMENTO = 'AGRUPADO'
    group by O.LOJA, O.CODORCAMENTO, O.DATASTATUS, I.CODPRODUTO),

AGRUPADO
as (select A.LOJA, A.CODAGRUPAMENTO, A.CODORCAMENTO as CODAGRUPADO, O.DATASTATUS as DATAAGRUPADO, O.OPERADOR,
           I.CODPRODUTO, sum(I.QUANTIDADE * I.PRECO * (1 -
           case
             when O.TOTALPRODUTOS = 0 then 0
             else case
                    when O.DESCONTOR <= 0 then O.DESCONTOR / O.TOTALPRODUTOS
                    else O.DESCONTOR / (O.TOTALPRODUTOS - coalesce(O.TOTALPRODUTOSPROMOCAO, 0)) * case
                                                                                                    when I.DATAPROMOCAO is null then 1
                                                                                                    else 0
                                                                                                  end
                  end
           end +
           case
             when O.TOTALPRODUTOS = 0 then 0
             else case
                    when O.ENCARGOSFINANCEIROS >= 0 then O.ENCARGOSFINANCEIROS / O.TOTALPRODUTOS
                    else O.ENCARGOSFINANCEIROS / (O.TOTALPRODUTOS - coalesce(O.TOTALPRODUTOSPROMOCAO, 0)) * case
                                                                                                              when I.DATAPROMOCAO is null then 1
                                                                                                              else 0
                                                                                                            end
                  end
           end +
           case
             when O.TOTALPRODUTOS = 0 then 0
             else coalesce(O.OUTRASDESPESAS, 0) / O.TOTALPRODUTOS
           end)) / sum(I.QUANTIDADE) as PRECOAGRUPADO,
           sum(I.QUANTIDADE) as QUANTIDADE, sum(coalesce((select sum(ID.QUANTIDADE)
                                                          from ITEMSPRODDEV ID
                                                          join ORCAMENTOS OD on OD.LOJA = ID.LOJADEV and OD.CODORCAMENTO = ID.CODORCAMENTODEV
                                                          where ID.LOJA = I.LOJA and
                                                                ID.CODORCAMENTO = I.CODORCAMENTO and
                                                                ID.NUMITEM = I.NUMITEM and
                                                                (OD.STATUS not in (11, 10) or OD.DATACANCELAMENTO > O.DATACANCELAMENTO)), 0)) as QUANTIDADEDEV
    from ORCAGRUPADOS A
    join ORCAMENTOS O on O.LOJA = A.LOJA and O.CODORCAMENTO = A.CODORCAMENTO
    join ITEMSPROD I on I.LOJA = O.LOJA and I.CODORCAMENTO = O.CODORCAMENTO
    group by A.LOJA, A.CODAGRUPAMENTO, A.CODORCAMENTO, O.DATASTATUS, O.OPERADOR, I.CODPRODUTO)

select V.LOJA, V.CODAGRUPAMENTO, V.DATAAGRUPAMENTO, A.CODAGRUPADO, A.DATAAGRUPADO, A.OPERADOR, V.CODPRODUTO,
       A.QUANTIDADE, A.QUANTIDADEDEV, V.PRECOAGRUPAMENTO * (A.QUANTIDADE - A.QUANTIDADEDEV) as TOTALFINAL,
       V.PRECOAGRUPAMENTO, V.PRECOAGRUPAMENTO * A.QUANTIDADE as TOTALAGRUPAMENTO, A.PRECOAGRUPADO,
       A.PRECOAGRUPADO * A.QUANTIDADE as TOTALAGRUPADO
from AGRUPAMENTO V
join AGRUPADO A on A.LOJA = V.LOJA and A.CODAGRUPAMENTO = V.CODAGRUPAMENTO and A.CODPRODUTO = V.CODPRODUTO
where V.DATAAGRUPAMENTO >= :DATA1 and
      V.DATAAGRUPAMENTO < :DATA2