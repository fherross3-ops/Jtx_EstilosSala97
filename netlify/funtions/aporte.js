// ============================================================
// Netlify Function: aporte.js
// POST -> agrega aporte(s) al CSV en GitHub
// GET  -> devuelve el listado actual de aportes (JSON)
// ============================================================

const CONTRATOS = {
  'C01': ['01','02','03','04','10','11','12','13','14','19','20','21','22','23'],
  'C02': ['05','06','07','08','09','15','16','17','18','24','25','26','27','28'],
  'C03': ['29','30','31','32','33','38','39','40','41','42','48','49','50','51'],
  'C04': ['34','35','36','37','43','44','45','46','47','52','53','54','55','56'],
  'C05': ['57','58','59','60','61','66','67','68','69','70','75','76','77'],
  'C06': ['62','63','64','65','71','72','73','74','78','79','80','81','82'],
  'C07': ['91','92','94','95','96','97','98','99','100','101','102','103','111','112','113'],
  'C08': ['83','84','85','86','87','88','89','90','93'],
  'C09': ['105','106'],
  'C10': ['107','108','109','110']
};

function contratoDeTelar(telar) {
  const t = String(telar || '').padStart(2, '0');
  for (const c in CONTRATOS) if (CONTRATOS[c].indexOf(t) !== -1) return c;
  return 'SIN_CONTRATO';
}

function escapeCSV(v) {
  const s = String(v == null ? '' : v);
  if (s.indexOf(',') !== -1 || s.indexOf('"') !== -1 || s.indexOf('\n') !== -1) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function parseCSVLine(line) {
  const out = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQ) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQ = false;
      } else cur += ch;
    } else {
      if (ch === ',') { out.push(cur); cur = ''; }
      else if (ch === '"') inQ = true;
      else cur += ch;
    }
  }
  out.push(cur);
  return out;
}

exports.handler = async (event) => {
  const TOKEN  = process.env.GITHUB_PAT_TOKEN;
  const REPO   = process.env.GITHUB_REPO;
  const PATH   = process.env.GITHUB_APORTES_PATH || 'aportes/historial.csv';
  const BRANCH = process.env.GITHUB_BRANCH || 'main';

  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  if (!TOKEN || !REPO) {
    return { statusCode: 500, headers: cors, body: 'Falta GITHUB_PAT_TOKEN o GITHUB_REPO' };
  }

  const apiUrl = `https://api.github.com/repos/${REPO}/contents/${PATH}`;
  const headers = {
    Authorization: `token ${TOKEN}`,
    'User-Agent': 'jeantex-aportes',
    Accept: 'application/vnd.github+json'
  };

  // ---------------- GET: leer aportes ----------------
  if (event.httpMethod === 'GET') {
    try {
      const res = await fetch(`${apiUrl}?ref=${BRANCH}`, { headers });
      if (res.status === 404) {
        return { statusCode: 200, headers: { ...cors, 'Content-Type': 'application/json' }, body: '[]' };
      }
      if (!res.ok) return { statusCode: 500, headers: cors, body: await res.text() };
      const j = await res.json();
      const csv = Buffer.from(j.content, 'base64').toString('utf-8');
      const lineas = csv.split('\n').filter(l => l.trim());
      lineas.shift(); // encabezado
      const aportes = lineas.map(l => {
        const [fecha, hora, nombre, telar, contrato, lote, estilo, clase, descripcion] = parseCSVLine(l);
        return { fecha, hora, nombre, telar, contrato, lote, estilo, clase, descripcion };
      });
      return {
        statusCode: 200,
        headers: { ...cors, 'Content-Type': 'application/json' },
        body: JSON.stringify(aportes)
      };
    } catch (err) {
      return { statusCode: 500, headers: cors, body: String(err) };
    }
  }

  // ---------------- POST: crear aporte(s) ----------------
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers: cors, body: 'Method Not Allowed' };
  }

  try {
    const body = JSON.parse(event.body || '{}');
    const nombre = String(body.nombre || '').trim();
    const lista = Array.isArray(body.aportes) ? body.aportes : [];

    if (!nombre || !lista.length) {
      return { statusCode: 400, headers: cors, body: 'Falta nombre o aportes' };
    }

    // 1. Leer CSV actual
    let contenidoActual = 'fecha,hora,nombre,telar,contrato,lote,estilo,clase,descripcion\n';
    let sha = null;
    const getRes = await fetch(`${apiUrl}?ref=${BRANCH}`, { headers });
    if (getRes.ok) {
      const j = await getRes.json();
      sha = j.sha;
      contenidoActual = Buffer.from(j.content, 'base64').toString('utf-8');
    }
    if (!contenidoActual.endsWith('\n')) contenidoActual += '\n';

    // 2. Construir nuevas filas
    const now = new Date();
    const fecha = now.toISOString().slice(0, 10);
    const hora = now.toISOString().slice(11, 16);

    let nuevas = '';
    for (const a of lista) {
      const telar = String(a.telar || '').padStart(2, '0');
      const contrato = contratoDeTelar(telar);
      nuevas += [
        fecha, hora,
        escapeCSV(nombre), telar, contrato,
        escapeCSV(a.lote), escapeCSV(a.estilo),
        escapeCSV(a.clase), escapeCSV(a.descripcion)
      ].join(',') + '\n';
    }

    // 3. Commit
    const putBody = {
      message: `Aporte(s) ${fecha} ${hora} · ${lista.length} línea(s)`,
      content: Buffer.from(contenidoActual + nuevas).toString('base64'),
      branch: BRANCH
    };
    if (sha) putBody.sha = sha;

    const putRes = await fetch(apiUrl, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(putBody)
    });

    if (!putRes.ok) {
      return { statusCode: 500, headers: cors, body: await putRes.text() };
    }

    return {
      statusCode: 200,
      headers: { ...cors, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ok: true, insertados: lista.length })
    };
  } catch (err) {
    return { statusCode: 500, headers: cors, body: String(err) };
  }
};
