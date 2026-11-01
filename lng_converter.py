"""Converte um arquivo de nomes traduzidos (.lng) feito para um banco de dados para outro banco.

O .lng (lido por database_load_language_names, 0x5339a0, Database.cpp) tem 8 u32 de quantidades e depois os
registros de cada tabela, sem id: o registro i vale para a entidade i do banco (ver docs/LNG_FORMAT.md).
Por isso um .lng só serve ao banco para o qual foi feito; num banco com outras quantidades o jogo recusa o arquivo
(Database.cpp 7784) e fica com os nomes em inglês.

A conversão casa cada entidade do banco novo com a do banco velho pelo nome em inglês (com a nação ou a cidade,
nas tabelas onde o nome se repete) e copia a tradução; o que não casa fica com o registro vazio (zeros e 0xff nos
bytes de gênero), que o jogo lê como "manter o nome do banco". Entidade renomeada entre os bancos não casa: fica
sem tradução e sai no relatório, para o tradutor conferir.

No `eng.lng`, use --completar: o jogo também o carrega com outros idiomas (0x544fc0, Database.cpp 19953 se as
quantidades não batem) e os acessores dele (ex. 0x5457dc) devolvem o texto do registro sem cair no nome do banco;
com --completar, a entidade sem par recebe os textos do próprio banco novo em vez do registro vazio.

Uso: python lng_converter.py <entrada.lng> <Data do banco da entrada> <Data do banco novo> <saída.lng> [--completar] [-v]
"""
import os
import struct
import sys
from collections import defaultdict

# (nome, campo do cabeçalho, tamanho no .lng, arquivos do banco, tamanho no banco, tamanho do nome no banco,
#  bytes de gênero no .lng). Na ordem do arquivo. O registro do .lng espelha os textos do banco a partir do +4
#  (a cidade é a exceção: 51 bytes de nome no .lng contra 26 no banco).
SECOES = [
    ('clubes', 0, 0x4f, ('club.dat', 'nat_club.dat'), 581, 51, (0x33, 0x4e)),
    ('continentes', 1, 0xba, ('continent.dat',), 198, 26, (0x1a, 0x9e, 0xb9)),
    ('competições de seleções', 2, 0x53, ('nation_comp.dat',), 107, 51, (0x33, 0x4e)),
    ('nações', 3, 0x6d, ('nation.dat',), 290, 51, (0x33, 0x4e)),
    ('estádios', 6, 0x34, ('stadium.dat',), 78, 51, (0x33,)),
    ('cidades', 4, 0x34, ('city.dat',), 56, 26, (0x33,)),
    ('competições de pessoal', 7, 0x4f, ('staff_comp.dat',), 101, 51, (0x33, 0x4e)),
    ('competições de clubes', 5, 0x53, ('club_comp.dat',), 107, 51, (0x33, 0x4e)),
]
# onde fica o id do "dono" do nome, para separar homônimos: (tabela do dono, deslocamento no registro do banco)
DONO = {'clubes': ('nações', 0x53), 'cidades': ('nações', 0x1f), 'estádios': ('cidades', 0x38)}


def texto(b):
    return b.split(b'\0')[0]


def vazio(sec):
    r = bytearray(sec[2])
    for g in sec[6]:
        r[g] = 0xff
    return bytes(r)


def do_banco(sec, reg):
    """O registro do .lng com os textos do próprio registro do banco (para --completar)."""
    if sec[0] == 'cidades':  # 26 bytes de nome no banco, 51 no .lng
        return reg[4:30].ljust(0x33, b'\0') + reg[0x1e:0x1f]
    return reg[4:4 + sec[2]]


def tem_texto(reg, sec):
    """O registro traz algum texto (fora dos bytes de gênero)?"""
    return any(b for i, b in enumerate(reg) if i not in sec[6])


def ler_lng(caminho):
    d = open(caminho, 'rb').read()
    cab = struct.unpack('<8I', d[:32])
    if cab[0] == 0xf1fffff1:
        sys.exit('%s: formato com a marca 0xf1fffff1 (bytes trocados): não suportado' % caminho)
    regs, p = {}, 32
    for sec in SECOES:
        n, t = cab[sec[1]], sec[2]
        regs[sec[0]] = [d[p + i * t:p + (i + 1) * t] for i in range(n)]
        p += n * t
    if p != len(d):
        sys.exit('%s: tamanho %d, o cabeçalho pede %d' % (caminho, len(d), p))
    return regs


def ler_banco(data):
    banco = {}
    for nome, _, _, arqs, reg, _, _ in SECOES:
        d = b''.join(open(os.path.join(data, a), 'rb').read() for a in arqs)
        banco[nome] = [d[i:i + reg] for i in range(0, len(d) - reg + 1, reg)]
    return banco


def chaves(banco):
    """{tabela: [chaves da 1ª passada, da 2ª...]}: o nome em inglês com o nome do dono (DONO), depois só o
    nome (salva o clube de uma nação renomeada, ex. Holland -> Netherlands); nas nações, depois a sigla."""
    nomes = {s[0]: [texto(r[4:4 + s[5]]) for r in banco[s[0]]] for s in SECOES}
    k = {}
    for s in SECOES:
        dono = DONO.get(s[0])
        if dono:
            tab, ofs = dono
            ids = [struct.unpack_from('<i', r, ofs)[0] for r in banco[s[0]]]
            donos = [nomes[tab][i] if 0 <= i < len(nomes[tab]) else None for i in ids]
            k[s[0]] = [list(zip(nomes[s[0]], donos)), nomes[s[0]]]
            if s[0] == 'clubes':  # clube renomeado (Ajax -> Ajax Amsterdam) costuma manter o nome curto
                curtos = [texto(r[0x38:0x52]) for r in banco[s[0]]]
                k[s[0]] += [list(zip(curtos, donos)), curtos]
        elif s[0] == 'nações':
            k[s[0]] = [nomes[s[0]], [texto(r[0x53:0x57]) for r in banco[s[0]]]]
        else:
            k[s[0]] = [nomes[s[0]]]
    return k


def casar(passadas_v, passadas_n):
    """{entidade nova: entidade velha}. Em cada passada, entre as que sobraram: chave única nos dois bancos, ou,
    entre homônimos, a mesma posição (é o que faz o banco igual voltar idêntico)."""
    par = {}
    for n, (kv, kn) in enumerate(zip(passadas_v, passadas_n)):
        usadas = set(par.values())
        pv, pn = defaultdict(list), defaultdict(list)
        for i, k in enumerate(kv):
            if i not in usadas:
                pv[k].append(i)
        for j, k in enumerate(kn):
            if j not in par:
                pn[k].append(j)
        for j, k in enumerate(kn):
            if j in par or (n and not (k[0] if isinstance(k, tuple) else k)):
                continue  # da 2ª passada em diante, chave vazia não casa
            c = pv.get(k, [])
            if len(c) == 1 and len(pn[k]) == 1:
                par[j] = c[0]
            elif j in c:
                par[j] = j
    return par


def converter(lng, data_velho, data_novo, completar=False):
    """(bytes do .lng novo, relatório {tabela: dict})."""
    regs = ler_lng(lng)
    velho, novo = ler_banco(data_velho), ler_banco(data_novo)
    for s in SECOES:
        if len(regs[s[0]]) != len(velho[s[0]]):
            sys.exit('%s: %d %s, o banco %s tem %d: o .lng não é deste banco' % (
                lng, len(regs[s[0]]), s[0], data_velho, len(velho[s[0]])))
    kv, kn = chaves(velho), chaves(novo)
    saida, rel = [], {}
    for s in SECOES:
        nome, branco = s[0], vazio(s)
        k1v, k1n = kv[nome][0], kn[nome][0]
        par = casar(kv[nome], kn[nome])
        velhas = set(k1v)
        r = {'banco novo': len(k1n), 'traduzidas': 0, 'casadas sem tradução no original': 0,
             'sem par (ficam em inglês)': 0, 'homônimas sem par': 0, 'amostras': [], 'renomeadas': []}
        for j, k in enumerate(k1n):
            i = par.get(j)
            if i is None:
                saida.append(do_banco(s, novo[nome][j]) if completar else branco)
                r['homônimas sem par' if k in velhas else 'sem par (ficam em inglês)'] += 1
                continue
            saida.append(regs[nome][i])
            if not tem_texto(regs[nome][i], s):
                r['casadas sem tradução no original'] += 1
            else:
                r['traduzidas'] += 1
                if (i != j or k1v[i] != k) and len(r['amostras']) < 8:
                    r['amostras'].append((i, j, k1v[i], k, texto(regs[nome][i])))
        usadas = set(par.values())
        perdidas = [i for i, x in enumerate(regs[nome]) if tem_texto(x, s) and i not in usadas]
        r['traduções perdidas'] = len(perdidas)
        r['perdidas'] = [(k1v[i], texto(regs[nome][i])) for i in perdidas if texto(regs[nome][i])]
        # nas tabelas de posição estável (sem DONO), a tradução perdida cuja posição, no banco novo, é de uma
        # entidade sem par: provável renomeação (ou vaga reaproveitada, ex. Andorra -> Kosovo: por isso não se copia)
        for i in perdidas if nome not in DONO else []:
            if i < len(k1n) and i not in par:
                r['renomeadas'].append((k1v[i], k1n[i], texto(regs[nome][i])))
        rel[nome] = r
    cab = [0] * 8
    for s in SECOES:
        cab[s[1]] = len(kn[s[0]][0])
    return struct.pack('<8I', *cab) + b''.join(saida), rel


def mostra(k):
    if isinstance(k, tuple):
        return '%s (%s)' % (mostra(k[0]), mostra(k[1]) if k[1] is not None else '-')
    return k.decode('latin-1')


def main():
    args = [a for a in sys.argv[1:] if a not in ('-v', '--completar')]
    if len(args) != 4:
        sys.exit(__doc__)
    dados, rel = converter(*args[:3], completar='--completar' in sys.argv)
    open(args[3], 'wb').write(dados)
    print('gravado %s (%d bytes)\n' % (args[3], len(dados)))
    print('%-26s %7s %10s %12s %9s %10s %9s' % ('tabela', 'novo', 'traduzidas', 'casadas s/t', 'sem par',
                                               'homônimas', 'perdidas'))
    for nome, r in rel.items():
        print('%-26s %7d %10d %12d %9d %10d %9d' % (nome, r['banco novo'], r['traduzidas'],
                                                     r['casadas sem tradução no original'],
                                                     r['sem par (ficam em inglês)'], r['homônimas sem par'],
                                                     r['traduções perdidas']))
    print('\n"casadas s/t": a entidade existe nos dois, mas o .lng de entrada já não a traduzia;'
          '\n"perdidas": traduções da entrada sem entidade correspondente no banco novo.')
    lim = None if '-v' in sys.argv else 15
    for nome, r in rel.items():
        if r['renomeadas']:
            print('\n%s: tradução perdida, outro nome na mesma posição do banco novo (fica em inglês; '
                  'tradução antiga entre colchetes):' % nome)
            for a, b, t in r['renomeadas'][:lim]:
                print('  %s -> %s   [%s]' % (mostra(a), mostra(b), t.decode('latin-1')))
            if lim and len(r['renomeadas']) > lim:
                print('  ... mais %d (-v mostra todas)' % (len(r['renomeadas']) - lim))
        elif nome in DONO and r['perdidas']:
            print('\n%s: traduções perdidas (sem par no banco novo):' % nome)
            for a, t in r['perdidas'][:lim]:
                print('  %s   [%s]' % (mostra(a), t.decode('latin-1')))
            if lim and len(r['perdidas']) > lim:
                print('  ... mais %d (-v mostra todas)' % (len(r['perdidas']) - lim))
        if r['amostras']:
            print('\n%s casadas em outra posição ou com outro dono (velha -> nova):' % nome)
            for i, j, a, b, t in r['amostras']:
                print('  %5d -> %5d  %s -> %s = %s' % (i, j, mostra(a), mostra(b), t.decode('latin-1')))


if __name__ == '__main__':
    main()
