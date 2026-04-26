import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_URL = "https://raw.githubusercontent.com/chickenX002/pokedex-api/main/pokemon_data_remapped.json"
SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"

_pokemon_db = None

def get_db():
    global _pokemon_db
    if _pokemon_db is None:
        resp = requests.get(DB_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _pokemon_db = {p["name"].lower(): p for p in data}
    return _pokemon_db


def get_sprites(name: str, pid: int):
    """
    Calls PokéAPI to get the correct sprite URLs for any form.
    Regional variants (sandshrew-alola, slowpoke-galar, etc.) and megas
    all have their own high internal IDs (10000+) in the sprite repo.
    PokéAPI's /pokemon/<name> response has the exact correct URLs already —
    we just read them directly instead of constructing from the dex ID.
    """
    try:
        r = requests.get(
            f"https://pokeapi.co/api/v2/pokemon/{name}",
            timeout=8,
            headers={"User-Agent": "pokedex-app/1.0"}
        )
        if r.ok:
            data = r.json()
            # PokéAPI's own `id` field is the sprite repo ID for forms (e.g. 10164)
            sprite_id = data.get("id", pid)
            normal = f"{SPRITE_BASE}/other/official-artwork/{sprite_id}.png"
            shiny  = f"{SPRITE_BASE}/other/official-artwork/shiny/{sprite_id}.png"
            return normal, shiny
    except Exception:
        pass
    # Fallback — correct for base forms, wrong for regional variants if API is down
    return (
        f"{SPRITE_BASE}/other/official-artwork/{pid}.png",
        f"{SPRITE_BASE}/other/official-artwork/shiny/{pid}.png",
    )


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Pokédex</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Nunito:wght@400;600;700;900&display=swap" rel="stylesheet" />
  <style>
    :root {
      --red: #e3350d;
      --dark-red: #9b1a04;
      --yellow: #ffcb05;
      --darker: #0d0d1a;
      --card-bg: #16213e;
      --text: #e8e0ce;
      --muted: #8888aa;
      --radius: 16px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Nunito', sans-serif;
      background: var(--darker);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
    }

    body::before {
      content: '';
      position: fixed; inset: 0;
      background-image: radial-gradient(circle, #ffffff08 1px, transparent 1px);
      background-size: 28px 28px;
      pointer-events: none;
      z-index: 0;
    }

    header {
      position: relative;
      background: linear-gradient(135deg, var(--red) 0%, var(--dark-red) 100%);
      padding: 24px 32px 20px;
      display: flex;
      align-items: center;
      gap: 20px;
      box-shadow: 0 4px 20px #00000060;
      z-index: 10;
    }

    .pokeball-icon { width: 52px; height: 52px; flex-shrink: 0; }

    header h1 {
      font-family: 'Press Start 2P', monospace;
      font-size: clamp(14px, 3vw, 22px);
      color: var(--yellow);
      text-shadow: 3px 3px 0 #00000050;
      letter-spacing: 2px;
    }

    header p { font-size: 13px; color: rgba(255,255,255,0.7); margin-top: 4px; }

    main {
      position: relative;
      z-index: 1;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }

    .search-wrap { position: relative; margin-bottom: 40px; }

    .search-wrap input {
      width: 100%;
      padding: 18px 60px 18px 24px;
      font-family: 'Nunito', sans-serif;
      font-size: 18px;
      font-weight: 700;
      border: 3px solid transparent;
      border-radius: 50px;
      background: var(--card-bg);
      color: var(--text);
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      box-shadow: 0 4px 20px #00000040;
    }

    .search-wrap input::placeholder { color: var(--muted); }
    .search-wrap input:focus {
      border-color: var(--yellow);
      box-shadow: 0 0 0 4px #ffcb0520, 0 4px 20px #00000040;
    }

    .search-btn {
      position: absolute;
      right: 10px; top: 50%;
      transform: translateY(-50%);
      background: var(--red);
      border: none;
      border-radius: 50%;
      width: 44px; height: 44px;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s, transform 0.1s;
    }
    .search-btn:hover { background: var(--dark-red); }
    .search-btn:active { transform: translateY(-50%) scale(0.93); }
    .search-btn svg { width: 20px; height: 20px; fill: white; }

    #autocomplete {
      position: absolute;
      top: calc(100% + 6px);
      left: 0; right: 0;
      background: var(--card-bg);
      border: 2px solid #ffffff15;
      border-radius: var(--radius);
      overflow: hidden;
      z-index: 100;
      display: none;
      box-shadow: 0 8px 30px #00000060;
    }
    #autocomplete.open { display: block; }
    #autocomplete li {
      list-style: none;
      padding: 12px 20px;
      cursor: pointer;
      font-weight: 600;
      text-transform: capitalize;
      transition: background 0.1s;
    }
    #autocomplete li:hover { background: #ffffff10; }

    #result { display: none; }

    .poke-card {
      background: var(--card-bg);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 16px 60px #00000070;
      border: 2px solid #ffffff0a;
      animation: slideUp 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(24px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .card-header {
      position: relative;
      padding: 40px 40px 0;
      display: flex;
      align-items: flex-end;
      min-height: 220px;
    }

    .card-header-bg {
      position: absolute; inset: 0;
      z-index: 0;
    }
    .card-header-bg::after {
      content: '';
      position: absolute;
      right: -40px; top: -40px;
      width: 260px; height: 260px;
      border-radius: 50%;
      border: 40px solid rgba(255,255,255,0.06);
    }

    .sprite-container { position: relative; z-index: 1; flex-shrink: 0; }

    #pokemon-sprite {
      width: 180px; height: 180px;
      filter: drop-shadow(0 8px 20px rgba(0,0,0,0.6));
      transition: transform 0.3s ease;
      cursor: pointer;
    }
    #pokemon-sprite:hover { transform: scale(1.08) translateY(-4px); }

    .sprite-toggle {
      position: absolute;
      bottom: 4px; right: 0;
      font-size: 10px;
      background: rgba(0,0,0,0.5);
      color: var(--yellow);
      border: none;
      border-radius: 8px;
      padding: 3px 8px;
      cursor: pointer;
      font-family: 'Press Start 2P', monospace;
    }

    .card-meta {
      position: relative;
      z-index: 1;
      padding: 0 0 24px 32px;
      flex: 1;
    }

    .pokemon-number {
      font-family: 'Press Start 2P', monospace;
      font-size: 13px;
      color: rgba(255,255,255,0.4);
      margin-bottom: 6px;
    }

    .pokemon-name {
      font-family: 'Press Start 2P', monospace;
      font-size: clamp(16px, 4vw, 26px);
      color: white;
      text-transform: capitalize;
      text-shadow: 2px 2px 0 rgba(0,0,0,0.3);
      margin-bottom: 16px;
      line-height: 1.4;
    }

    .types { display: flex; gap: 8px; flex-wrap: wrap; }

    .type-badge {
      padding: 5px 14px;
      border-radius: 50px;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: white;
      text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }

    .card-body { padding: 32px 40px; }

    .section-label {
      font-family: 'Press Start 2P', monospace;
      font-size: 9px;
      color: var(--muted);
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 12px;
    }

    .entry-text {
      font-size: 16px;
      line-height: 1.75;
      color: var(--text);
      background: rgba(255,255,255,0.04);
      border-left: 3px solid var(--yellow);
      padding: 16px 20px;
      border-radius: 0 12px 12px 0;
      font-style: italic;
    }

    #error-box {
      display: none;
      background: #3d0b00;
      border: 2px solid var(--red);
      border-radius: var(--radius);
      padding: 20px 24px;
      color: #ffaa88;
      font-weight: 700;
      text-align: center;
      animation: slideUp 0.3s ease;
    }

    #loading { display: none; text-align: center; padding: 60px 0; }

    .pokeball-spin {
      width: 64px; height: 64px;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 16px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    #loading p {
      font-family: 'Press Start 2P', monospace;
      font-size: 11px;
      color: var(--muted);
    }

    @media (max-width: 520px) {
      .card-header { flex-direction: column; align-items: center; padding: 24px 24px 0; min-height: auto; }
      .card-meta { padding: 16px 0 24px; text-align: center; }
      .types { justify-content: center; }
      .card-body { padding: 24px; }
    }
  </style>
</head>
<body>

<header>
  <svg class="pokeball-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="48" fill="white" stroke="#333" stroke-width="4"/>
    <path d="M2 50 Q2 2 50 2 Q98 2 98 50 Z" fill="#e3350d"/>
    <rect x="0" y="46" width="100" height="8" fill="#333" rx="2"/>
    <circle cx="50" cy="50" r="14" fill="white" stroke="#333" stroke-width="5"/>
    <circle cx="50" cy="50" r="7" fill="#f8f0d8"/>
  </svg>
  <div>
    <h1>POKÉDEX</h1>
    <p>Search your Pokémon database</p>
  </div>
</header>

<main>
  <div class="search-wrap">
    <input type="text" id="search-input" placeholder="Enter a Pokémon name…" autocomplete="off" />
    <button class="search-btn" id="search-btn" aria-label="Search">
      <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
    </button>
    <ul id="autocomplete"></ul>
  </div>

  <div id="loading">
    <svg class="pokeball-spin" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="48" fill="#16213e" stroke="#ffffff20" stroke-width="4"/>
      <path d="M2 50 Q2 2 50 2 Q98 2 98 50 Z" fill="#e3350d"/>
      <rect x="0" y="46" width="100" height="8" fill="#333"/>
      <circle cx="50" cy="50" r="14" fill="#16213e" stroke="#ffffff30" stroke-width="5"/>
      <circle cx="50" cy="50" r="7" fill="#ffcb05"/>
    </svg>
    <p>LOADING…</p>
  </div>

  <div id="error-box"></div>

  <div id="result">
    <div class="poke-card">
      <div class="card-header">
        <div class="card-header-bg" id="card-bg"></div>
        <div class="sprite-container">
          <img id="pokemon-sprite" src="" alt="Pokémon sprite" title="Click to toggle shiny!" />
          <button class="sprite-toggle" id="shiny-toggle">✨ SHINY</button>
        </div>
        <div class="card-meta">
          <div class="pokemon-number" id="pokemon-number"></div>
          <div class="pokemon-name" id="pokemon-name"></div>
          <div class="types" id="pokemon-types"></div>
        </div>
      </div>
      <div class="card-body">
        <div class="section-label">Pokédex Entry</div>
        <p class="entry-text" id="pokemon-entry"></p>
      </div>
    </div>
  </div>
</main>

<script>
  const TYPE_COLORS = {
    fire:'#ff6b35', water:'#4fc3f7', grass:'#66bb6a', electric:'#ffd54f',
    psychic:'#f48fb1', ice:'#80deea', dragon:'#7e57c2', dark:'#546e7a',
    fairy:'#f06292', normal:'#a1a1a1', fighting:'#e53935', flying:'#90caf9',
    poison:'#ab47bc', ground:'#d4a055', rock:'#8d6e63', bug:'#9ccc65',
    ghost:'#5c6bc0', steel:'#78909c'
  };

  const input    = document.getElementById('search-input');
  const btn      = document.getElementById('search-btn');
  const acList   = document.getElementById('autocomplete');
  const loading  = document.getElementById('loading');
  const errorBox = document.getElementById('error-box');
  const result   = document.getElementById('result');
  const spriteEl = document.getElementById('pokemon-sprite');
  const shinyBtn = document.getElementById('shiny-toggle');

  let currentData = null;
  let showingShiny = false;

  // Autocomplete
  let acTimer;
  input.addEventListener('input', () => {
    clearTimeout(acTimer);
    const q = input.value.trim();
    if (q.length < 2) { acList.classList.remove('open'); return; }
    acTimer = setTimeout(() => fetchAutocomplete(q), 200);
  });

  async function fetchAutocomplete(q) {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const names = await r.json();
    acList.innerHTML = '';
    if (!names.length) { acList.classList.remove('open'); return; }
    names.forEach(name => {
      const li = document.createElement('li');
      li.textContent = name.replace(/-/g, ' ');
      li.addEventListener('click', () => {
        input.value = name;
        acList.classList.remove('open');
        search(name);
      });
      acList.appendChild(li);
    });
    acList.classList.add('open');
  }

  document.addEventListener('click', e => {
    if (!e.target.closest('.search-wrap')) acList.classList.remove('open');
  });

  // Search
  btn.addEventListener('click', () => { acList.classList.remove('open'); search(input.value.trim()); });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') { acList.classList.remove('open'); search(input.value.trim()); }
  });

  async function search(name) {
    if (!name) return;
    result.style.display = 'none';
    errorBox.style.display = 'none';
    loading.style.display = 'block';

    try {
      const r = await fetch('/api/pokemon/' + encodeURIComponent(name.toLowerCase()));
      const data = await r.json();
      loading.style.display = 'none';

      if (!r.ok) {
        errorBox.textContent = data.error || 'Pokémon not found!';
        errorBox.style.display = 'block';
        return;
      }

      currentData = data;
      showingShiny = false;
      renderCard(data);
    } catch (err) {
      loading.style.display = 'none';
      errorBox.textContent = 'Network error — please try again.';
      errorBox.style.display = 'block';
    }
  }

  function renderCard(data) {
    document.getElementById('pokemon-number').textContent = '#' + String(data.id).padStart(3, '0');
    document.getElementById('pokemon-name').textContent = data.name.replace(/-/g, ' ');
    document.getElementById('pokemon-entry').textContent = data.entry;

    const typesEl = document.getElementById('pokemon-types');
    typesEl.innerHTML = '';
    data.types.forEach(t => {
      const span = document.createElement('span');
      span.className = 'type-badge';
      span.textContent = t;
      span.style.background = TYPE_COLORS[t] || '#777';
      typesEl.appendChild(span);
    });

    spriteEl.src = data.sprite;
    spriteEl.alt = data.name;

    const col = TYPE_COLORS[data.types[0]] || '#777';
    document.getElementById('card-bg').style.background =
      'linear-gradient(135deg, ' + col + '35, ' + col + '15)';

    result.style.display = 'block';
  }

  // Shiny toggle
  shinyBtn.addEventListener('click', toggleShiny);
  spriteEl.addEventListener('click', toggleShiny);

  function toggleShiny() {
    if (!currentData) return;
    showingShiny = !showingShiny;
    spriteEl.src = showingShiny ? currentData.shiny_sprite : currentData.sprite;
    shinyBtn.textContent = showingShiny ? '⭐ NORMAL' : '✨ SHINY';
  }
</script>

</body>
</html>"""


@app.route("/")
def index():
    return HTML


@app.route("/api/pokemon/<n>")
def pokemon_detail(n):
    db = get_db()
    pokemon = db.get(n.lower().strip())
    if not pokemon:
        return jsonify({"error": f"'{n}' was not found in the Pokédex."}), 404
    pid = pokemon["id"]
    sprite, shiny_sprite = get_sprites(pokemon["name"], pid)
    return jsonify({
        "id": pid,
        "name": pokemon["name"],
        "types": pokemon.get("types", []),
        "entry": pokemon.get("entry", "No Pokédex entry available."),
        "sprite": sprite,
        "shiny_sprite": shiny_sprite,
    })


@app.route("/api/search")
def search():
    q = request.args.get("q", "").lower().strip()
    db = get_db()
    if not q:
        return jsonify([])
    matches = sorted(n for n in db if n.startswith(q))
    return jsonify(matches[:10])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
