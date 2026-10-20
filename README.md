# Compression LZ77 : codage et décodage

Projet d'examen *Codage et traitement du signal*. Implémentation en Python de l'algorithme **LZ77**, tel qu'enseigné en cours (buffer de recherche, buffer d'entrée, triplets `(position, longueur, caractère)`), puis étendu aux fichiers réels : texte, audio, image et vidéo.

Aucune bibliothèque externe : seulement la bibliothèque standard de Python 3.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `lz77_cours.py` | LZ77 pas à pas sur du texte, avec le tableau du cours (buffer de recherche / buffer d'entrée / codage) |
| `lz77_fichiers.py` | LZ77 sur fichiers binaires : compression, décompression, mesures (`bench`) |
| `README.md` | Ce document |

## Le principe

À chaque étape, on cherche dans le **buffer de recherche** (les derniers caractères déjà codés) la plus longue séquence qui commence le **buffer d'entrée** (les prochains caractères à coder). On émet un triplet `(p, l, c)` :

- `p` : distance en arrière (1 = dernier caractère du buffer de recherche), `0` si aucune correspondance ;
- `l` : longueur de la correspondance, au maximum `taille du buffer d'entrée - 1` ;
- `c` : caractère qui suit la correspondance.

Règles : à longueur égale on garde la correspondance la plus proche, et une correspondance peut déborder dans le buffer d'entrée (par exemple `(3, 5, D)`). Le décodage rejoue les triplets : on recopie `l` caractères situés `p` positions en arrière, puis on ajoute `c`.

## Utilisation

### Exemple pas à pas (cours)

```bash
python3 lz77_cours.py encode CABRACADABRARRARRAD
python3 lz77_cours.py decode "(0,0,C) (0,0,A) (0,0,B) (0,0,R) (3,1,C) (2,1,D) (7,4,R) (3,5,D)"
```

Par défaut : buffer de recherche de 7 caractères, buffer d'entrée de 6 (options `--search` et `--lookahead`).

### Fichiers

```bash
python3 lz77_fichiers.py c fichier.txt fichier.lz77        # compresser
python3 lz77_fichiers.py d fichier.lz77 fichier_out.txt    # décompresser
sha256sum fichier.txt fichier_out.txt                      # les deux empreintes doivent être identiques
python3 lz77_fichiers.py bench texte.txt audio.wav image.bmp video.mp4 --csv resultats.csv
```

Par défaut : buffer de recherche de 4095 octets, buffer d'entrée de 16. Un triplet occupe alors 12 + 4 + 8 = 24 bits.

## Format du fichier compressé

```
"LZ77" | taille recherche (4 o) | taille entrée (4 o) | taille originale (8 o) | triplets (bits)
```

Ce format est propre au projet : il n'est pas compatible avec gzip, zip ou 7-zip.

## Vérification

- Les exemples du cours sont reproduits exactement (par exemple `CABRACADABRARRARRAD` donne 8 triplets).
- La version « fichiers » donne les mêmes triplets que la version « cours » (vérifié sur 4 000 textes aléatoires).
- Aller-retour compression puis décompression identique à l'original, vérifié par SHA-256.

## Résultats

*(à remplir avec la sortie de la commande `bench` et les captures d'écran du PDF)*

| Type | Fichier | Original | Compressé | Taux | Aller-retour |
|---|---|---|---|---|---|
| Texte | texte.txt | 147,3 Ko | 34,6 Ko | 23,5 % | OK |
| Audio | audio.wav | 130,7 Ko | 182,2 Ko | 139,4 % | OK |
| Image | image.bmp | 225,1 Ko | 43,9 Ko | 19,5 % | OK |
| Vidéo | video.mp4 | 37,0 Ko | 44,6 Ko | 120,6 % | OK |

## Limites

- Chaque triplet contient toujours un caractère, donc un octet sans correspondance coûte 3 octets : les données déjà compressées (MP3, JPEG, MP4) ou aléatoires **grossissent** au lieu de rétrécir. C'est une propriété du LZ77 de base, pas un bug.
- Les fichiers peu répétitifs (audio brut bruité, image dégradée) compressent peu ou pas.
- La recherche de correspondances examine au plus 64 candidats par position, pour garder un temps raisonnable en Python.
- Pistes d'amélioration : un bit indicateur littéral/correspondance (LZSS), un codage entropique (Huffman) des triplets, un buffer de recherche plus grand.
