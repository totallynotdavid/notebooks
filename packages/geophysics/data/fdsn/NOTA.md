# Datos FDSN del sismo de Pisco de 2007

Metadatos StationXML y trazas miniSEED de las estaciones del conjunto de
`data/sac/`, canal BHZ, descargados de los servicios web FDSN: EarthScope
(`https://service.iris.edu`) para los metadatos y las trazas de G, II e IU, y el
datacentro de GEOFON (`geofon.gfz.de`) para la traza de GE. La ventana de cada
traza es un minuto antes a doce minutos después de la llegada teórica de la onda
P en iasp91.

- Estaciones: ANMO, ASCN, BBSR, BORG, COR, DWPF, EFI, KIP, MBO, MPG, PAB, PFO,
  PMSA, POHA, PTCN, QSPA, RPN, RSSD, SBA, SFJD, SJG, SUR, TAM, TAOE, TSUM, TUC,
  WCI, XMAS
- Fecha de descarga: 2026-11-25
- Archivos: `estaciones.xml` (metadatos con respuesta instrumental) y un
  `*.mseed` por estación (formas de onda en miniSEED).

Para volver a descargar:
`uv run --package geophysics python -m adquisicion.fdsn`.
