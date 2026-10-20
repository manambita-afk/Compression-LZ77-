#!/usr/bin/env python3
"""LZ77 tel qu'enseigne en cours : buffer de recherche + buffer d'entree.

Convention (deduite des deux exemples du professeur) :
  * buffer de recherche = 7 caracteres, buffer d'entree = 6 caracteres ;
  * chaque etape produit un triplet (position, longueur, caractere) :
      - position  = distance de retour en arriere, 1 = dernier caractere du
                    buffer de recherche (0 si aucune correspondance) ;
      - longueur  = nombre de caracteres identiques trouves (max = entree - 1,
                    car il faut garder 1 caractere pour la 3e composante) ;
      - caractere = le caractere qui suit la correspondance ;
  * (0, 0, c) = pas de correspondance, on emet le caractere c tel quel ;
  * a egalite de longueur, on prend la correspondance la plus proche ;
  * une correspondance peut deborder dans le buffer d'entree (ex. (3, 5, D)).

Usage :
    python3 lz77_cours.py encode CABRACADABRARRARRAD
    python3 lz77_cours.py decode "(0,0,C) (0,0,A) (0,0,B) (0,0,R) (3,1,C)"
    python3 lz77_cours.py encode TEXTE --search 7 --lookahead 6 --quiet
"""
import argparse, re, sys

SEARCH, LOOKAHEAD = 7, 6


def encode(text, search=SEARCH, lookahead=LOOKAHEAD):
    """Retourne (tokens, trace). trace = liste de (cellules_recherche, cellules_entree, token_precedent)."""
    n, pos, tokens = len(text), 0, []

    def window(p):
        s = text[max(0, p - search):p]
        i = text[p:p + lookahead]
        return [""] * (search - len(s)) + list(s), list(i) + [""] * (lookahead - len(i))

    trace = [window(0) + (None,)]
    while pos < n:
        max_len = min(lookahead - 1, n - pos - 1)
        best_len, best_off = 0, 0
        for off in range(1, min(search, pos) + 1):            # du plus proche au plus lointain
            length = 0
            while length < max_len and text[pos - off + length] == text[pos + length]:
                length += 1                                    # debordement autorise
            if length > best_len:
                best_len, best_off = length, off
        tok = (best_off, best_len, text[pos + best_len])
        tokens.append(tok)
        pos += best_len + 1
        trace.append(window(pos) + (tok,))
    return tokens, trace


def decode(tokens):
    out = []
    for off, length, ch in tokens:
        for _ in range(length):
            out.append(out[-off])                              # copie caractere par caractere
        out.append(ch)
    return "".join(out)


def fmt_token(t):
    return f"({t[0]}, {t[1]}, {t[2]})"


def print_table(text, tokens, trace, search=SEARCH, lookahead=LOOKAHEAD):
    print(f"Texte : {text}\n")
    w = 3
    print(f"{'Recherche':^{search * (w + 1) - 1}}", end="")
    print(" | " + f"{'Entree':^{lookahead * (w + 1) - 1}}" + " | Codage")
    for srch, inp, tok in trace:
        cells_s = " ".join(f"{c:^{w}}" for c in srch)
        cells_i = " ".join(f"{c:^{w}}" for c in inp)
        print(f"{cells_s} | {cells_i} | {fmt_token(tok) if tok else ''}")
    print(f"\nCode : {' '.join(fmt_token(t) for t in tokens)}")
    print(f"{len(text)} caracteres -> {len(tokens)} triplets")


def parse_tokens(s):
    found = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(.)\s*\)", s)
    if not found:
        sys.exit("Aucun triplet reconnu. Format attendu : (0,0,C) (3,1,A) ...")
    return [(int(a), int(b), c) for a, b, c in found]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["encode", "decode"])
    ap.add_argument("data", help="texte a coder, ou triplets a decoder")
    ap.add_argument("--search", type=int, default=SEARCH, help="taille du buffer de recherche (defaut 7)")
    ap.add_argument("--lookahead", type=int, default=LOOKAHEAD, help="taille du buffer d'entree (defaut 6)")
    ap.add_argument("--quiet", action="store_true", help="n'afficher que le code")
    a = ap.parse_args()
    if a.mode == "encode":
        toks, trace = encode(a.data, a.search, a.lookahead)
        if a.quiet:
            print(" ".join(fmt_token(t) for t in toks))
        else:
            print_table(a.data, toks, trace, a.search, a.lookahead)
        assert decode(toks) == a.data, "erreur interne : decodage different"
    else:
        print(decode(parse_tokens(a.data)))


if __name__ == "__main__":
    main()
