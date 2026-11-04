"""PDFs v2: acrescenta a página "Book it the easy way / Reserva fácil" no fim de cada guia,
com links de afiliado Travelpayouts (conta do Luiz, marker 595928, links gerados em 04/11/2026).
Uso: python3 v2_pagina_reserva.py  -> grava tudo em payhip/v2/ (originais não são tocados)."""
import io, os, zipfile
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color

F = "/mnt/skills/examples/canvas-design/canvas-fonts/"
for n, f in [("Tit", "BricolageGrotesque-Bold.ttf"), ("Txt", "InstrumentSans-Regular.ttf"),
             ("TxtB", "InstrumentSans-Bold.ttf"), ("Mono", "JetBrainsMono-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(n, F + f))
INK, TEAL, GRAY, LINE, SOFT = (Color(22/255, 33/255, 47/255), Color(15/255, 110/255, 140/255),
                              Color(90/255, 100/255, 114/255), Color(220/255, 225/255, 231/255),
                              Color(240/255, 246/255, 248/255))
W, H, M = 420, 596, 34

L = {  # links curtos gerados no painel da Travelpayouts
    "klook": {"rio": "https://klook.tpx.lu/Cm2EdUZa", "foz": "https://klook.tpx.lu/Me4YnVPs",
              "floripa": "https://klook.tpx.lu/9f5Wqbid", "salvador": "https://klook.tpx.lu/No8O4gNU",
              "sp": "https://klook.tpx.lu/yxUARXRi", "paraty": "https://klook.tpx.lu/zddShyc7",
              "lencois": "https://klook.tpx.lu/egUtcPWB", "camboriu": "https://klook.tpx.lu/NTzzfjAn"},
    "tiqets": {"rio": "https://tiqets.tpx.lu/LDjpTQOP", "foz": "https://tiqets.tpx.lu/e3gsdx5s",
               "sp": "https://tiqets.tpx.lu/aP235Qte", "salvador": "https://tiqets.tpx.lu/yjw5ens9"},
    "transfer": "https://gettransfer.tpx.lu/0spKIxKh", "carro": "https://getrentacar.tpx.lu/Hh7jnqny",
    "esim": "https://airalo.tpx.lu/7leGh4Sn", "mala": "https://radicalstorage.tpx.lu/hgDEJ0kh",
}
CARRO = {"foz", "floripa", "paraty", "camboriu"}  # destinos onde carro faz sentido

T = {
 "en": dict(label="BOOK IT THE EASY WAY", title="Book before you fly",
   intro="The few things worth sorting out before the trip, with the sites we use ourselves. "
         "Tap any card to open it.",
   klook=("Tours & experiences", "Day trips, boat rides and guided walks in {c}, with free cancellation on most."),
   tiqets=("Attraction tickets", "Skip-the-line tickets for the big sights in {c}. Booked online, shown on your phone."),
   transfer=("Airport transfer", "A fixed price from the airport to your door, agreed before you land."),
   carro=("Rental car", "Compare local and international rental companies. Worth it for the beaches and day trips."),
   esim=("eSIM for Brazil", "Mobile data from the moment you land, for maps, Uber and WhatsApp. No shop queue."),
   mala=("Luggage storage", "Night flight, or arriving before check-in? Leave your bags for the day near the center."),
   open="Open", tip="Tip: book tours and transfers at least 48 h ahead in high season (Dec–Mar and July).",
   disc="These are affiliate links. You pay the same price, and we may earn a small commission "
        "that keeps this guide updated. We only list services that make sense for this trip.",
   foot="Verified Oct 2026"),
 "es": dict(label="RESERVA FÁCIL", title="Resérvalo antes de viajar",
   intro="Lo poco que conviene dejar listo antes del viaje, con los sitios que usamos nosotros. "
         "Toca cualquier tarjeta para abrirla.",
   klook=("Tours y experiencias", "Excursiones, paseos en barco y visitas guiadas en {c}, la mayoría con cancelación gratis."),
   tiqets=("Entradas a atracciones", "Entradas sin fila para lo imperdible de {c}. Compra online y muéstralas en el celular."),
   transfer=("Traslado del aeropuerto", "Precio cerrado del aeropuerto a tu alojamiento, acordado antes de aterrizar."),
   carro=("Alquiler de auto", "Compara rentadoras locales e internacionales. Vale la pena para playas y excursiones."),
   esim=("eSIM para Brasil", "Datos móviles desde que aterrizas, para mapas, Uber y WhatsApp. Sin filas en tiendas."),
   mala=("Guardar equipaje", "¿Vuelo de noche o llegas antes del check-in? Deja tus maletas el día entero cerca del centro."),
   open="Abrir", tip="Consejo: en temporada alta (dic–mar y julio) reserva tours y traslados con 48 h de anticipación.",
   disc="Son enlaces de afiliado. Pagas el mismo precio y podemos ganar una pequeña comisión "
        "que mantiene esta guía actualizada. Solo incluimos servicios que tienen sentido para este viaje.",
   foot="Verificado oct 2026"),
}

def quebra(txt, fonte, tam, larg):
    linhas, atual = [], ""
    for p in txt.split():
        t = (atual + " " + p).strip()
        if pdfmetrics.stringWidth(t, fonte, tam) <= larg: atual = t
        else: linhas.append(atual); atual = p
    return linhas + [atual]

def pagina(lang, chave, cidade, rodape, num):
    t = T[lang]; buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    y = H - 46
    c.setFillColor(TEAL); c.setFont("Mono", 7.5); c.drawString(M, y, t["label"])
    y -= 26; c.setFillColor(INK); c.setFont("Tit", 21); c.drawString(M, y, t["title"])
    y -= 18; c.setFont("Txt", 9.2); c.setFillColor(GRAY)
    for ln in quebra(t["intro"], "Txt", 9.2, W - 2*M): c.drawString(M, y, ln); y -= 12.5
    itens = [("klook", L["klook"][chave])]
    if chave in L["tiqets"]: itens.append(("tiqets", L["tiqets"][chave]))
    itens += [("transfer", L["transfer"]), ("esim", L["esim"])]
    if chave in CARRO: itens.append(("carro", L["carro"]))
    itens.append(("mala", L["mala"]))
    y -= 10; alt = 64 if len(itens) <= 5 else 60
    for k, url in itens:
        nome, desc = t[k]; desc = desc.format(c=cidade)
        topo = y; base = y - alt + 9
        c.setFillColor(SOFT); c.setStrokeColor(LINE); c.roundRect(M, base, W - 2*M, topo - base, 6, fill=1, stroke=1)
        c.setFillColor(INK); c.setFont("TxtB", 10.2); c.drawString(M + 12, topo - 19, nome)
        c.setFont("Txt", 8.4); c.setFillColor(GRAY); yy = topo - 33
        for ln in quebra(desc, "Txt", 8.4, W - 2*M - 86)[:2]: c.drawString(M + 12, yy, ln); yy -= 10.5
        bx = W - M - 58; by = base + (topo - base)/2 - 9
        c.setFillColor(TEAL); c.roundRect(bx, by, 48, 18, 9, fill=1, stroke=0)
        c.setFillColor(Color(1, 1, 1)); c.setFont("TxtB", 8.5); c.drawCentredString(bx + 24, by + 5.6, t["open"] + " →")
        c.linkURL(url, (M, base, W - M, topo), relative=0)
        y -= alt
    y -= 14; c.setFillColor(INK); c.setFont("TxtB", 8.6)
    for ln in quebra(t["tip"], "TxtB", 8.6, W - 2*M): c.drawString(M, y, ln); y -= 11.5
    y -= 4; c.setFont("Txt", 7.6); c.setFillColor(GRAY)
    for ln in quebra(t["disc"], "Txt", 7.6, W - 2*M): c.drawString(M, y, ln); y -= 10
    c.setStrokeColor(LINE); c.line(M, 30, W - M, 30)
    c.setFont("Mono", 6.6); c.setFillColor(GRAY); c.drawString(M, 18, rodape)
    c.drawRightString(W - M, 18, f"{t['foot']} · {num}")
    c.save(); buf.seek(0); return PdfReader(buf).pages[0]

B = "/home/claude/"
GUIAS = [  # arquivo original, idioma, chave, nome da cidade no texto, rodapé
 ("payhip/01-EN-rio/Quick-Budget-Guide-Rio-EN.pdf", "en", "rio", "Rio", "Quick Budget Guide — Rio de Janeiro"),
 ("payhip/02-EN-iguazu/Quick-Budget-Guide-Iguazu-Falls-EN.pdf", "en", "foz", "Foz do Iguaçu", "Quick Budget Guide — Foz do Iguaçu"),
 ("payhip/03-EN-florianopolis/Quick-Budget-Guide-Florianopolis-EN.pdf", "en", "floripa", "Florianópolis", "Quick Budget Guide — Florianópolis"),
 ("payhip/04-EN-salvador/Quick-Budget-Guide-Salvador-EN.pdf", "en", "salvador", "Salvador", "Quick Budget Guide — Salvador"),
 ("payhip/05-EN-saopaulo/Quick-Budget-Guide-Sao-Paulo-EN.pdf", "en", "sp", "São Paulo", "Quick Budget Guide — São Paulo"),
 ("payhip/06-EN-paraty/Quick-Budget-Guide-Paraty-EN.pdf", "en", "paraty", "Paraty", "Quick Budget Guide — Paraty"),
 ("payhip/07-EN-lencois/Quick-Budget-Guide-Lencois-Maranhenses-EN.pdf", "en", "lencois", "Lençóis Maranhenses", "Quick Budget Guide — Lençóis Maranhenses"),
 ("payhip/08-ES-rio/Quick-Budget-Guide-Rio-ES.pdf", "es", "rio", "Río", "Quick Budget Guide — Rio de Janeiro"),
 ("payhip/09-ES-foz/Quick-Budget-Guide-Cataratas-ES.pdf", "es", "foz", "Foz do Iguaçu", "Quick Budget Guide — Foz do Iguaçu"),
 ("payhip/10-ES-floripa/Quick-Budget-Guide-Florianopolis-ES.pdf", "es", "floripa", "Florianópolis", "Quick Budget Guide — Florianópolis"),
 ("payhip/11-ES-salvador/Quick-Budget-Guide-Salvador-ES.pdf", "es", "salvador", "Salvador", "Quick Budget Guide — Salvador"),
 ("payhip/12-ES-saopaulo/Quick-Budget-Guide-Sao-Paulo-ES.pdf", "es", "sp", "São Paulo", "Quick Budget Guide — São Paulo"),
 ("payhip/13-ES-paraty/Quick-Budget-Guide-Paraty-ES.pdf", "es", "paraty", "Paraty", "Quick Budget Guide — Paraty"),
 ("payhip/14-ES-lencois/Quick-Budget-Guide-Lencois-Maranhenses-ES.pdf", "es", "lencois", "Lençóis Maranhenses", "Quick Budget Guide — Lençóis Maranhenses"),
 ("payhip/18-EN-carnaval/Quick-Budget-Guide-Rio-Carnival-2027-EN.pdf", "en", "rio", "Rio", "Quick Budget Guide — Rio Carnival 2027"),
 ("payhip/19-EN-camboriu/Quick-Budget-Guide-Balneario-Camboriu-EN.pdf", "en", "camboriu", "Balneário Camboriú", "Quick Budget Guide — Balneário Camboriú"),
 ("payhip-es/Gumroad-Camboriu-ES/Gumroad-Camboriu-ES/3-CONTENT-Quick-Budget-Guide-Balneario-Camboriu-ES.pdf", "es", "camboriu", "Balneário Camboriú", "Quick Budget Guide — Balneário Camboriú"),
 ("payhip-es/Gumroad-Carnaval-2027-ES/Gumroad-Carnaval-2027-ES/3-CONTENT-Quick-Budget-Guide-Carnaval-Rio-2027-ES.pdf", "es", "rio", "Río", "Quick Budget Guide — Carnaval de Río 2027"),
]
PACOTES = [("payhip/15-EN-pacote-7/EN-pacote-7.zip"), ("payhip/16-ES-pacote-7/ES-pacote-7.zip"),
           ("payhip/17-ES-pack-floripa-iguazu/ES-pack-floripa-iguazu.zip")]

if __name__ == "__main__":
    out = B + "payhip/v2/"; os.makedirs(out, exist_ok=True); novos = {}
    for arq, lang, chave, cidade, rod in GUIAS:
        r = PdfReader(B + arq); w = PdfWriter(clone_from=r)
        w.add_page(pagina(lang, chave, cidade, rod, len(r.pages) + 1))
        nome = os.path.basename(arq).replace("3-CONTENT-", "")
        pasta = arq.split("/")[1] if arq.startswith("payhip/") else ("20-ES-camboriu" if "Camboriu" in arq else "21-ES-carnaval")
        os.makedirs(out + pasta, exist_ok=True)
        with open(out + pasta + "/" + nome, "wb") as f: w.write(f)
        novos[os.path.basename(arq)] = out + pasta + "/" + nome
    for z in PACOTES:
        pasta = z.split("/")[1]; os.makedirs(out + pasta, exist_ok=True)
        with zipfile.ZipFile(B + z) as zi, zipfile.ZipFile(out + pasta + "/" + os.path.basename(z), "w", zipfile.ZIP_DEFLATED) as zo:
            for n in zi.namelist():
                if n in novos: zo.write(novos[n], n)
                else: zo.writestr(n, zi.read(n))
    print("ok", len(novos), "pdfs +", len(PACOTES), "pacotes")
