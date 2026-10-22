"""
Contabilino - Genera logo e icone dal disegno vettoriale del logo
(il "conto a T" della partita doppia, con gli importi in Dare e in Avere).

    pip install pillow
    python strumenti/genera_icone.py

Produce:
    docs/assets/logo.png        logo per il sito (256 px)
    risorse/contabilino.ico     icona dell'eseguibile Windows (16-256 px)
    risorse/contabilino.icns    icona dell'app per Mac (16-1024 px)
    icona.py                    icone della finestra e caselle di spunta, incorporate nel codice
"""

import base64
import io
import os

from PIL import Image, ImageDraw

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDE = (22, 101, 82)
BIANCO = (255, 255, 255)
GIALLO = (245, 184, 0)
ACCENTO = (0, 95, 184)       # blu di Windows 11
BORDO_SPUNTA = (138, 138, 138)


def logo(size):
    """Logo disegnato a 4x e ridotto, per bordi puliti a ogni dimensione."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 5, fill=VERDE)
    w = s // 11
    # Conto a T: barra orizzontale e verticale
    d.rectangle([s * 0.18, s * 0.28, s * 0.82, s * 0.28 + w], fill=BIANCO)
    d.rectangle([s / 2 - w / 2, s * 0.28, s / 2 + w / 2, s * 0.80], fill=BIANCO)
    # Importi in Dare (a sinistra) e in Avere (a destra)
    for i, y in enumerate((0.46, 0.60)):
        d.rectangle([s * 0.22, s * y, s * 0.40, s * y + w * 0.55], fill=GIALLO if i == 0 else BIANCO)
        d.rectangle([s * 0.60, s * y, s * 0.78, s * y + w * 0.55], fill=BIANCO if i == 0 else GIALLO)
    return im.resize((size, size), Image.LANCZOS)


def logo_nitido(size):
    """
    Logo per le misure piccole (fino a 32 px): stesse forme, ma con i bordi
    allineati ai pixel, così nella barra delle applicazioni resta nitido.
    Coordinate pensate su una griglia di 16 e moltiplicate per size / 16.
    """
    k = size / 16
    r = lambda v: int(round(v * k))
    im = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, size * 4 - 1, size * 4 - 1], radius=size * 4 // 5, fill=VERDE)
    im = im.resize((size, size), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    spessore = max(1, r(1.5))
    d.rectangle([r(3), r(4), r(13) - 1, r(4) + spessore - 1], fill=BIANCO)        # barra della T
    d.rectangle([r(7), r(4), r(9) - 1, r(13) - 1], fill=BIANCO)                   # gamba della T
    riga = max(1, r(1))
    for i, y in enumerate((7.5, 10)):
        d.rectangle([r(3), r(y), r(6) - 1, r(y) + riga - 1], fill=GIALLO if i == 0 else BIANCO)
        d.rectangle([r(10), r(y), r(13) - 1, r(y) + riga - 1], fill=BIANCO if i == 0 else GIALLO)
    return im


def icona(size):
    return logo_nitido(size) if size <= 32 else logo(size)


def spunta(size, piena):
    """Casella di spunta in stile Windows 11: vuota (bordo grigio) o piena (blu con segno bianco)."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    margine = s * 0.12
    box = [margine, margine, s - margine, s - margine]
    raggio = s * 0.18
    if piena:
        d.rounded_rectangle(box, radius=raggio, fill=ACCENTO)
        punti = [(s * 0.30, s * 0.52), (s * 0.44, s * 0.66), (s * 0.71, s * 0.37)]
        d.line(punti, fill=BIANCO, width=max(4, int(s * 0.09)), joint="curve")
    else:
        d.rounded_rectangle(box, radius=raggio, fill=BIANCO, outline=BORDO_SPUNTA, width=max(4, int(s * 0.06)))
    return im.resize((size, size), Image.LANCZOS)


def png_base64(immagine):
    buf = io.BytesIO()
    immagine.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    logo(256).save(os.path.join(RADICE, "docs", "assets", "logo.png"))

    os.makedirs(os.path.join(RADICE, "risorse"), exist_ok=True)
    misure = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    immagini = [icona(m) for m in misure]
    immagini[-1].save(
        os.path.join(RADICE, "risorse", "contabilino.ico"),
        sizes=[(m, m) for m in misure], append_images=immagini[:-1],
    )
    # Mac: l'immagine più grande; Pillow ricava le altre misure dell'icona
    logo(1024).save(os.path.join(RADICE, "risorse", "contabilino.icns"))

    righe = [
        '"""',
        "Contabilino - Icone della finestra e caselle di spunta (PNG codificati in base64).",
        "File generato da strumenti/genera_icone.py: non modificarlo a mano.",
        '"""',
        "",
        "ICONE = {",
    ]
    for size in (16, 24, 32, 48, 64, 128):
        righe.append(f'    {size}: "{png_base64(icona(size))}",')
    righe.append("}")
    righe += ["", "# Caselle di spunta per gli elenchi: misura → (vuota, piena)", "SPUNTE = {"]
    for size in (16, 20, 24, 32):
        righe.append(f'    {size}: ("{png_base64(spunta(size, False))}", "{png_base64(spunta(size, True))}"),')
    righe.append("}")
    with open(os.path.join(RADICE, "icona.py"), "w", encoding="utf-8") as f:
        f.write("\n".join(righe) + "\n")


if __name__ == "__main__":
    main()
