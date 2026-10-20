#!/usr/bin/env python3
"""LZ77 sur fichiers : meme principe que le cours (triplets position/longueur/octet),
mais avec des buffers plus grands et un format binaire compact.

Principe (identique a lz77_cours.py) :
  * buffer de recherche = les `search` derniers octets deja codes ;
  * buffer d'entree     = les `lookahead` prochains octets a coder ;
  * a chaque etape on cherche la plus longue correspondance (a egalite : la plus
    proche), puis on emet (position, longueur, octet_suivant) ;
  * (0, 0, c) = aucune correspondance ;
  * la longueur maximale est lookahead - 1 ; une correspondance peut deborder.

Format du fichier compresse :
    "LZ77" | search (I) | lookahead (I) | taille_originale (Q) | triplets
  Chaque triplet occupe ob + lb + 8 bits, avec ob = bits de la position,
  lb = bits de la longueur (par defaut 12 + 4 + 8 = 24 bits = 3 octets).

Usage :
    python3 lz77_fichiers.py c fichier.txt fichier.lz77
    python3 lz77_fichiers.py d fichier.lz77 fichier_restaure.txt
    python3 lz77_fichiers.py bench texte.txt audio.wav image.bmp video.mp4 --csv resultats.csv
"""
import argparse, hashlib, os, struct, sys, time, zlib

MAGIC = b"LZ77"
SEARCH, LOOKAHEAD = 4095, 16      # defaut : 12 bits de position, 4 bits de longueur
DEPTH = 64                        # nombre max de candidats examines par position


def bits_needed(max_value):
    return max(1, max_value.bit_length())


# ------------------------------------------------------------------ codage
def tokens(data, search=SEARCH, lookahead=LOOKAHEAD, depth=DEPTH):
    """Liste de triplets (position, longueur, octet) - meme regles que lz77_cours.py."""
    n, pos, ins = len(data), 0, 0
    table, last, out = {}, [-1] * 256, []
    while pos < n:
        for p in range(ins, pos):                         # indexe les positions deja passees
            last[data[p]] = p
            if p + 1 < n:
                table.setdefault((data[p] << 8) | data[p + 1], []).append(p)
        ins = pos
        max_len = min(lookahead - 1, n - pos - 1)
        best_len = best_off = 0
        if max_len >= 2:
            cands = table.get((data[pos] << 8) | data[pos + 1])
            if cands:
                i, tried = len(cands) - 1, 0
                while i >= 0 and tried < depth:
                    c = cands[i]
                    off = pos - c
                    if off > search:
                        break
                    ln = 2
                    while ln < max_len and data[c + ln] == data[pos + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len, best_off = ln, off
                        if ln == max_len:
                            break
                    i -= 1
                    tried += 1
        if best_len == 0 and max_len >= 1:
            lp = last[data[pos]]
            if lp != -1 and pos - lp <= search:
                best_len, best_off = 1, pos - lp
        out.append((best_off, best_len, data[pos + best_len]))
        pos += best_len + 1
    return out


def compress(data, search=SEARCH, lookahead=LOOKAHEAD):
    ob, lb = bits_needed(search), bits_needed(lookahead - 1)
    total = ob + lb + 8
    out = bytearray(MAGIC + struct.pack(">IIQ", search, lookahead, len(data)))
    acc = nb = 0
    for off, ln, ch in tokens(data, search, lookahead):
        acc = (acc << total) | (off << (lb + 8)) | (ln << 8) | ch
        nb += total
        while nb >= 8:
            nb -= 8
            out.append((acc >> nb) & 0xFF)
        acc &= (1 << nb) - 1
    if nb:
        out.append((acc << (8 - nb)) & 0xFF)
    return bytes(out)


def decompress(blob):
    if blob[:4] != MAGIC:
        raise ValueError("Ce n'est pas un fichier LZ77 de ce projet")
    search, lookahead, size = struct.unpack_from(">IIQ", blob, 4)
    ob, lb = bits_needed(search), bits_needed(lookahead - 1)
    total = ob + lb + 8
    out = bytearray()
    acc = nb = 0
    pos, end = 20, len(blob)
    mask_o, mask_l = (1 << ob) - 1, (1 << lb) - 1
    while len(out) < size:
        while nb < total:
            if pos >= end:
                raise ValueError("Fichier tronque")
            acc = (acc << 8) | blob[pos]
            pos += 1
            nb += 8
        nb -= total
        v = (acc >> nb) & ((1 << total) - 1)
        acc &= (1 << nb) - 1
        off, ln, ch = (v >> (lb + 8)) & mask_o, (v >> 8) & mask_l, v & 0xFF
        if off > len(out) or (ln and off == 0):
            raise ValueError("Triplet invalide (fichier corrompu)")
        for _ in range(ln):                                # copie octet par octet (debordement permis)
            out.append(out[-off])
        out.append(ch)
    return bytes(out[:size])


# ------------------------------------------------------------------ utilitaires
def human(n):
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or u == "Go":
            return f"{n} o" if u == "o" else f"{n:.1f} {u}"
        n /= 1024


def cmd_bench(a):
    head = f"{'Fichier':<24}{'Original':>11}{'Compresse':>11}{'Taux':>8}{'gzip -9':>11}{'Comp.':>8}{'Decomp.':>9}  Verif."
    print(head); print("-" * len(head))
    rows = []
    for path in a.files:
        raw = open(path, "rb").read()
        t = time.time(); comp = compress(raw, a.search, a.lookahead); tc = time.time() - t
        t = time.time(); back = decompress(comp); td = time.time() - t
        ok = hashlib.sha256(back).digest() == hashlib.sha256(raw).digest()
        ref = len(zlib.compress(raw, 9))
        print(f"{os.path.basename(path)[:23]:<24}{human(len(raw)):>11}{human(len(comp)):>11}"
              f"{100 * len(comp) / max(len(raw), 1):>7.1f}%{human(ref):>11}{tc:>7.1f}s{td:>8.1f}s  {'OK' if ok else 'ECHEC'}")
        rows.append((path, len(raw), len(comp), ref, round(tc, 2), round(td, 2), ok))
    if a.csv:
        with open(a.csv, "w") as f:
            f.write("fichier,original,compresse,gzip9,temps_comp,temps_decomp,ok\n")
            for r in rows:
                f.write(",".join(map(str, r)) + "\n")
        print(f"\nResultats ecrits dans {a.csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("c", "d"):
        p = sub.add_parser(name); p.add_argument("src"); p.add_argument("dst")
        p.add_argument("--search", type=int, default=SEARCH); p.add_argument("--lookahead", type=int, default=LOOKAHEAD)
    b = sub.add_parser("bench"); b.add_argument("files", nargs="+"); b.add_argument("--csv")
    b.add_argument("--search", type=int, default=SEARCH); b.add_argument("--lookahead", type=int, default=LOOKAHEAD)
    a = ap.parse_args()
    if a.cmd == "bench":
        return cmd_bench(a)
    raw = open(a.src, "rb").read()
    t = time.time()
    res = compress(raw, a.search, a.lookahead) if a.cmd == "c" else decompress(raw)
    open(a.dst, "wb").write(res)
    print(f"{a.src} ({human(len(raw))}) -> {a.dst} ({human(len(res))}) en {time.time() - t:.1f} s")


if __name__ == "__main__":
    main()
