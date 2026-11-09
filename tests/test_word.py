"""El texto de los bloques sin Markdown a la vista (ADR-020): párrafos ↔ Markdown de la carpeta de datos, y Word de ida
y vuelta (exportar, importar el exportado e importar un Word cualquiera)."""
from __future__ import annotations

import io
import zipfile

import pytest

from pccf import bloques, texto, word
from pccf.datos import WordSinBloque
from pccf.texto import Parrafo

from .conftest import CURSO

MD = """### Organización del taller

Párrafo con **negrita** y un [enlace](https://example.com/norma) en medio.
Sigue el mismo párrafo.

- Primera viñeta
- Segunda con **negrita**

> Nota para el equipo: no sale en el PCCF.

Último párrafo."""

PARRAFOS = [
    Parrafo("subtitulo", "Organización del taller"),
    Parrafo("parrafo", "Párrafo con **negrita** y un [enlace](https://example.com/norma) en medio. Sigue el mismo "
                       "párrafo."),
    Parrafo("vineta", "Primera viñeta"),
    Parrafo("vineta", "Segunda con **negrita**"),
    Parrafo("nota", "Nota para el equipo: no sale en el PCCF."),
    Parrafo("parrafo", "Último párrafo."),
]


def test_markdown_a_parrafos_y_vuelta():
    assert texto.de_markdown(MD) == PARRAFOS
    md = texto.a_markdown(PARRAFOS)
    assert texto.de_markdown(md) == PARRAFOS
    assert "- Primera viñeta\n- Segunda" in md          # las viñetas, seguidas
    assert md.startswith("### Organización del taller\n\nPárrafo")


def test_trozos_juntan_el_mismo_formato_y_el_enlace_no_lleva_negrita():
    ts = [texto.Trozo("Uno "), texto.Trozo("dos", True), texto.Trozo(" tres", True),
          texto.Trozo("web", True, "https://example.com")]
    assert texto.de_trozos(ts) == "Uno **dos tres**[web](https://example.com)"
    assert texto.de_trozos([texto.Trozo("Título", True)], negrita=False) == "Título"
    assert texto.sin_marcas("a **b** [c](https://x.example)") == "a b c"


def _crear(datos, contenido: str = MD):
    b = datos.nuevo_bloque("PRU", CURSO, 6, "ciclo", "metodologia", "Equipo ficticio", "2030-01-02")
    return bloques.guardar(b, contenido, "2030-01-02")


def test_exportar_e_importar_el_mismo_bloque(datos, tmp_path):
    b = _crear(datos)
    docx = bloques.a_word(b, "PCCF PRU · apartado 6")
    imp = word.importar(docx)
    assert imp.parrafos == PARRAFOS                       # el aviso de arriba no entra
    assert imp.archivo == "metodologia.md" and "tipo: ciclo" in imp.cabecera
    archivo = tmp_path / "devuelto.docx"
    archivo.write_bytes(docx)
    with pytest.raises(FileExistsError):
        datos.importar_bloque(archivo, "PRU", CURSO, hoy="2030-02-03")
    nuevo = datos.importar_bloque(archivo, "PRU", CURSO, sustituir=True, hoy="2030-02-03")
    assert nuevo.ruta == b.ruta and nuevo.estado == "borrador" and nuevo.fecha == "2030-02-03"
    assert texto.de_markdown(nuevo.cuerpo) == PARRAFOS


def test_el_word_lleva_estilos_de_word_y_el_enlace(datos):
    docx = bloques.a_word(_crear(datos), "Prueba")
    z = zipfile.ZipFile(io.BytesIO(docx))
    doc = z.read("word/document.xml").decode()
    assert 'w:pStyle w:val="Heading2"' in doc and 'w:pStyle w:val="ListBullet"' in doc
    assert 'w:pStyle w:val="NotaInterna"' in doc and "<w:b/>" in doc and "<w:hyperlink" in doc
    assert "https://example.com/norma" in z.read("word/_rels/document.xml.rels").decode()
    assert "PCCF bloque" in z.read("docProps/custom.xml").decode()


def _docx(cuerpo: str, estilos: str = "", rels: str = "") -> bytes:
    """Un Word mínimo «de otra aplicación», con datos ficticios."""
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as z:
        z.writestr("word/document.xml", f"<w:document {ns}><w:body>{cuerpo}</w:body></w:document>")
        z.writestr("word/styles.xml", f"<w:styles {ns}>{estilos}</w:styles>")
        z.writestr("word/_rels/document.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f"{rels}</Relationships>")
    return salida.getvalue()


def test_importar_un_word_cualquiera():
    estilos = ('<w:style w:type="paragraph" w:styleId="Ttulo1"><w:name w:val="heading 1"/></w:style>'
               '<w:style w:type="paragraph" w:styleId="Prrafodelista"><w:name w:val="List Paragraph"/></w:style>'
               '<w:style w:type="character" w:styleId="Textoennegrita"><w:name w:val="Strong"/></w:style>')
    rels = ('<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'hyperlink" Target="https://example.com/" TargetMode="External"/>')
    cuerpo = (
        '<w:p><w:pPr><w:pStyle w:val="Ttulo1"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Criterios</w:t></w:r></w:p>'
        '<w:p><w:r><w:t xml:space="preserve">Texto con </w:t></w:r><w:r><w:rPr><w:b/><w:i/><w:color w:val="FF0000"/>'
        '</w:rPr><w:t>negrita</w:t></w:r><w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve"> y </w:t></w:r>'
        '<w:hyperlink r:id="rId9"><w:r><w:t>enlace</w:t></w:r></w:hyperlink>'
        '<w:del><w:r><w:delText>borrado</w:delText></w:r></w:del></w:p>'
        '<w:p><w:pPr><w:pStyle w:val="Prrafodelista"/><w:numPr><w:ilvl w:val="1"/><w:numId w:val="3"/></w:numPr>'
        '</w:pPr><w:r><w:rPr><w:rStyle w:val="Textoennegrita"/></w:rPr><w:t>Una</w:t></w:r>'
        '<w:r><w:t xml:space="preserve"> viñeta</w:t></w:r></w:p>'
        '<w:p/>'
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Celda</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
    )
    imp = word.importar(_docx(cuerpo, estilos, rels))
    assert imp.cabecera is None and imp.archivo is None
    assert imp.parrafos == [
        Parrafo("subtitulo", "Criterios"),
        Parrafo("parrafo", "Texto con **negrita** y [enlace](https://example.com/)"),
        Parrafo("vineta", "**Una** viñeta"),
        Parrafo("parrafo", "Celda"),
    ]
    assert any("tablas" in a for a in imp.avisos)


def test_un_word_sin_bloque_o_que_no_es_word(datos, tmp_path):
    suelto = tmp_path / "texto.docx"
    suelto.write_bytes(_docx("<w:p><w:r><w:t>Hola</w:t></w:r></w:p>"))
    with pytest.raises(WordSinBloque):
        datos.importar_bloque(suelto, "PRU", CURSO)
    with pytest.raises(word.WordNoValido):
        word.importar(b"no es un zip")


def test_un_bloque_de_la_version_anterior_sigue_entrando(datos, carpeta, tmp_path):
    suelto = tmp_path / "empresas.md"
    suelto.write_text("---\ntipo: anual\napartado: 9\norigen: equipo\nestado: borrador\naportado_por: Prueba\n"
                      "fecha: 2030-01-02\n---\n\nCriterios ficticios.\n", encoding="utf-8")
    assert datos.importar_bloque(suelto, "PRU", CURSO).ruta.name == "empresas.md"
