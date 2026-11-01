"""Janela do lng_converter.py, para quem não usa a linha de comando (os textos da janela são em inglês: é para o
fórum). Escolhe o .lng traduzido, a pasta Data do banco para o qual ele foi feito, a pasta Data do banco novo e a
pasta de saída; converte também o eng.lng (o jogo o lê com qualquer idioma) e grava um relatório ao lado.

Uso: python lng_converter_gui.py      (exe: pyinstaller --onefile --windowed lng_converter_gui.py)
"""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import lng_confere
import lng_converter as conv

NOMES_EN = {'clubes': 'clubs', 'continentes': 'continents', 'competições de seleções': 'national team comps',
            'nações': 'nations', 'estádios': 'stadiums', 'cidades': 'cities',
            'competições de pessoal': 'awards (staff comps)', 'competições de clubes': 'club comps'}


def mostra(k):
    if isinstance(k, tuple):
        return '%s (%s)' % (mostra(k[0]), mostra(k[1]) if k[1] is not None else '-')
    return k.decode('latin-1')


def relatorio(arquivo, rel, aceito, listas=True):
    """O relatório em inglês: quantidades por tabela e as traduções que ficaram sem par (renomeadas ou perdidas);
    sem as listas no eng.lng, onde toda entrada tem texto e a lista não ajuda ninguém."""
    out = ['%s: %s' % (arquivo, 'the game will accept this file' if aceito else 'WARNING: counts do not match'), '',
           '%-24s %7s %11s %13s %6s' % ('table', 'entries', 'translated', 'kept English', 'lost')]
    for nome, r in rel.items():
        out.append('%-24s %7d %11d %13d %6d' % (
            NOMES_EN[nome], r['banco novo'], r['traduzidas'],
            r['banco novo'] - r['traduzidas'], r['traduções perdidas']))
    out += ['', '"kept English": new in this database, renamed, or not translated in the original file.',
            '"lost": translations whose entry is not in the new database (or was renamed).']
    for nome, r in rel.items() if listas else []:
        if r['renomeadas']:
            out += ['', '%s renamed in the new database (now in English; old translation in brackets):' % NOMES_EN[nome]]
            out += ['  %s -> %s   [%s]' % (mostra(a), mostra(b), t.decode('latin-1')) for a, b, t in r['renomeadas']]
        elif nome in conv.DONO and r['perdidas']:
            out += ['', '%s translations with no match in the new database (renamed or removed):' % NOMES_EN[nome]]
            out += ['  %s   [%s]' % (mostra(a), t.decode('latin-1')) for a, t in r['perdidas']]
    return '\n'.join(out)


def converter(lng, velho, novo, saida, com_eng):
    """Converte o .lng (e o eng.lng da pasta velha, se pedido) para a pasta de saída; devolve o relatório."""
    tarefas = [(lng, False)]
    eng = os.path.join(velho, 'eng.lng')
    if com_eng and os.path.basename(lng).lower() != 'eng.lng':
        if not os.path.exists(eng):
            raise ValueError('eng.lng not found in %s (uncheck the option to skip it)' % velho)
        tarefas.append((eng, True))
    os.makedirs(saida, exist_ok=True)
    textos = []
    for origem, completar in tarefas:
        completar = completar or os.path.basename(origem).lower() == 'eng.lng'
        try:
            dados, rel = conv.converter(origem, velho, novo, completar=completar)
        except SystemExit as e:  # o lng_converter avisa por sys.exit
            raise ValueError('%s: %s' % (os.path.basename(origem), e))
        destino = os.path.join(saida, os.path.basename(origem))
        if os.path.exists(destino) and not os.path.exists(destino + '.bak'):
            shutil.copy2(destino, destino + '.bak')  # não perde o arquivo que estava lá
        open(destino, 'wb').write(dados)
        aceito = all(x[3] for x in lng_confere.conferir(destino, novo)[0])
        textos.append(relatorio(destino, rel, aceito, listas=not completar))
    texto = ('\n\n' + '=' * 70 + '\n\n').join(textos)
    open(os.path.join(saida, 'lng_converter_report.txt'), 'w', encoding='utf-8').write(texto)
    return texto


def janela():
    raiz = tk.Tk()
    raiz.title('CM 01/02 .lng converter')
    campos = {}
    linhas = [('lng', 'Translated .lng file', 'file'),
              ('velho', 'Data folder of the database it was made for', 'dir'),
              ('novo', 'Data folder of the new database', 'dir'),
              ('saida', 'Output folder', 'dir')]

    def escolher(chave, tipo):
        if tipo == 'file':
            v = filedialog.askopenfilename(filetypes=[('Language names', '*.lng'), ('All files', '*.*')])
            if v and not campos['velho'].get():
                campos['velho'].set(os.path.dirname(v))
        else:
            v = filedialog.askdirectory()
        if v:
            campos[chave].set(os.path.normpath(v))

    for n, (chave, rotulo, tipo) in enumerate(linhas):
        campos[chave] = tk.StringVar()
        tk.Label(raiz, text=rotulo).grid(row=n, column=0, sticky='w', padx=6, pady=3)
        tk.Entry(raiz, textvariable=campos[chave], width=70).grid(row=n, column=1, padx=6)
        tk.Button(raiz, text='Browse...', command=lambda c=chave, t=tipo: escolher(c, t)).grid(row=n, column=2, padx=6)
    com_eng = tk.BooleanVar(value=True)
    tk.Checkbutton(raiz, variable=com_eng,
                   text='Also convert eng.lng from the old Data folder (the game reads it with every language)'
                   ).grid(row=4, column=0, columnspan=3, sticky='w', padx=6)
    caixa = scrolledtext.ScrolledText(raiz, width=110, height=24, font=('Consolas', 9))
    caixa.grid(row=6, column=0, columnspan=3, padx=6, pady=6)

    def rodar():
        v = {k: x.get().strip() for k, x in campos.items()}
        if not all(v.values()):
            messagebox.showwarning('Missing', 'Fill in all four fields.')
            return
        if os.path.normcase(os.path.abspath(v['saida'])) == os.path.normcase(os.path.abspath(v['velho'])):
            messagebox.showwarning('Output', 'The output folder cannot be the old Data folder.')
            return
        caixa.delete('1.0', 'end')
        raiz.config(cursor='watch')
        raiz.update()
        try:
            texto = converter(v['lng'], v['velho'], v['novo'], v['saida'], com_eng.get())
        except (ValueError, OSError) as e:
            messagebox.showerror('Error', str(e))
            return
        finally:
            raiz.config(cursor='')
        caixa.insert('1.0', texto)
        messagebox.showinfo('Done', 'Files written to %s\n(report: lng_converter_report.txt; any file that was '
                                    'there before was kept as .bak)' % v['saida'])

    tk.Button(raiz, text='Convert', width=20, command=rodar).grid(row=5, column=0, columnspan=3, pady=4)
    raiz.mainloop()


if __name__ == '__main__':
    janela()
