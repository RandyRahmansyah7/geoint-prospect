# PRD — GEOINT Prospect (light analyst workstation)

Status: draft, 2026-10-27. Owner: Randy. Semua issue fitur merujuk ke dokumen ini lewat nomor
bagian (`§`) dan ID fitur (`F-xx`).

Cara pakai: setiap issue menyebut bagian PRD yang jadi acuannya + aturan desain `§2` yang wajib
dipatuhi. Kalau ada keputusan baru, perbarui PRD ini dulu, baru issue-nya.

## 1. Produk

Workstation desktop pribadi untuk discovery dan analisis geospasial. Lima workspace: Browser,
Graph, Gaia, Object Explorer, Dossier. Gaia = workspace peta, dan itulah yang di-clone dari
referensi visual. Tema terang, padat, tanpa branding.

## 2. Aturan desain (wajib, tidak bisa ditawar)

| ID | Aturan |
|----|--------|
| DR-1 | Tema terang saja: permukaan putih/near-white, border 1 px netral, tanpa shadow berat. Tema gelap di luar lingkup sampai diminta. |
| DR-2 | Tanpa branding: tanpa logo, wordmark, nama aplikasi di UI, avatar, akun, atau dashboard. Nama workspace (Gaia, Browser, …) hanya sebagai konteks navigasi. |
| DR-3 | Struktur repo tetap: Next.js App Router di root, `src-tauri/` untuk shell, `engine/` untuk Python, `database/` untuk schema/migrasi, `data/` untuk data lokal (git-ignored), `configs/` untuk konfigurasi. Dilarang membuat `frontend/` atau `backend/`. |
| DR-4 | Static export (`output: "export"`). Dilarang fitur Next yang butuh server: cookies/headers, middleware/proxy, rewrites/redirects, ISR, draft mode, Server Actions, optimasi `next/image` default, route handler dinamis. Dynamic route wajib `generateStaticParams()`. |
| DR-5 | Tanpa API server permanen dan tanpa database server. Komputasi analitik ada di `engine/` (dipanggil lokal atau cloud job nanti), kontraknya harus stabil dan terdokumentasi. |
| DR-6 | Ukuran padat (lihat §6): sidebar 240/56 px, baris navigasi 32 px, ikon 16 px, label 12 px, panel 248 px, rail 36 px, status bar 28 px, banner 20 px. |
| DR-7 | Kontrol yang belum berfungsi wajib `disabled` + punya nama aksesibel. Dilarang tombol yang diam-diam tidak melakukan apa-apa (no-op). |
| DR-8 | Aksesibilitas: tiap kontrol ikon punya nama aksesibel, focus ring terlihat, item navigasi aktif pakai `aria-current="page"`, item collapsed punya tooltip. |
| DR-9 | Dependency minimal: tambah library hanya untuk fitur konkret (MapLibre saat peta masuk, GeoPandas/Shapely saat analisis butuh). |
| DR-10 | Nama fitur UI mengikuti peta penamaan §5. Bahasa UI: Inggris. |
| DR-11 | Tanpa penandaan klasifikasi nyata. Banner tetap netral: `UNCLASSIFIED // DEMO WORKSPACE`. |
| DR-12 | Offline-first: tanpa permintaan jaringan kecuali fitur menuntutnya secara eksplisit dan disetujui di issue. |

## 3. Referensi visual dan lingkup clone

Referensi: 6 screenshot Palantir-style yang dikirim Randy. Yang di-clone adalah **varian terang**
(screenshot 1, 2, 3, 5): banner, panel kiri bertab, kanvas peta, rail ikon kanan, status bar,
panel Selection, editor geometri. Varian gelap (screenshot 4, 6: tab SEARCH/MAP/GRAPH, histogram,
timeline gelap) **di luar lingkup** selama tema terang belum selesai; fiturnya tetap tercatat di §4
supaya tidak hilang.

Yang tidak diambil dari referensi: branding, menu aplikasi (File/View/Related/Support), Share,
MTS/MNF, cuplikan klasifikasi nyata, data demo (Live Entities, SIGINT Notional, dsb).

## 4. Katalog fitur hasil clone

Kolom Status: issue yang mengerjakan, atau `ditunda` / `luar lingkup`.

| ID | Fitur di referensi | Adaptasi di software ini | Status |
|----|--------------------|--------------------------|--------|
| F-01 | Banner klasifikasi hijau di atas jendela | `UNCLASSIFIED // DEMO WORKSPACE`, 20 px, selebar jendela | selesai (#3) |
| F-02 | Panel kiri dengan tab Map layers / Data sources / Tools | Tab `Layers` / `Sources` / `Tools`, 248 px, bisa dilipat | selesai (#3) |
| F-03 | Chevron pelipat panel di tepi kanan panel | Tombol Collapse/Expand panel | selesai (#3) |
| F-04 | Kotak "Find…/Search this map" | Pencarian layer (filter daftar layer) | shell selesai (#3), fungsi di #7 |
| F-05 | Pohon layer bertingkat (grup, ikon per item, status sumber) | Pohon layer: visibilitas, opacity, urutan, jumlah fitur, filter | #7 |
| F-06 | "Create Order of Battle layer", pemilih Symbol, layer anotasi | "Create layer" + pemilih jenis geometri (belum ada data) | ditunda (butuh #7, #10) |
| F-07 | Kanvas peta (basemap + overlay + label) | Kanvas MapLibre, kontrol navigasi, skala, koordinat | #5 |
| F-08 | Pemilih basemap "CartoDB Light" + hitungan overlay | Pemilih basemap lokal (PMTiles di `data/`) + `Overlays: N` | #6, hitungan di #7 |
| F-09 | Strip alat peta + bar "Adding to <layer> + New" | Strip alat (select, gambar, ukur) — baru aktif saat ada layer | shell selesai (#3), fungsi ditunda |
| F-10 | Rail ikon kanan (legend, notes, histogram, timeline, dsb.) | Rail 36 px: Legend, Selection, Histogram, Timeline, Filter, Measure, Help | shell selesai (#3), isi menyusul |
| F-11 | Panel Selection: kartu objek, aksi, accordion Correlation/Details/Properties/Appearance | Panel inspector objek: properti + featured properties | #11 |
| F-12 | Status bar: Online/View/elemen interaktif, format koordinat, jam, badge Live | Status bar 28 px: state engine, basemap, overlay, format DD/DMS, jam | sebagian selesai (#3), sisanya #5/#6/#8 |
| F-13 | Indikator "Map health: Connected" | `Engine: online/offline` (status nyata dari proses engine) | #9 |
| F-14 | Timeline horizontal (sumbu tanggal, handle rentang, kontrol putar) | Kontrol waktu: sumbu waktu + rentang | #12 |
| F-15 | Histogram tipe event / hari (dari varian gelap) | Histogram waktu dari objek yang dimuat | #12 |
| F-16 | Jalur perjalanan dengan waypoint dan ring seleksi | Track/breadcrumb objek bergerak | #12 (butuh model waktu) |
| F-17 | Polygon, label, penanda lokasi di peta | Objek geometri + label dari layer | #10 |
| F-18 | Editor "Create shape": polygon/line/ring, daftar koordinat, nama, kategori, Finish/Cancel, edit vertex | Editor geometri: gambar polygon/line/point, isi koordinat manual, simpan ke `database/` | ditunda (butuh #10, #8) |
| F-19 | Chip klasifikasi pada objek ("MOCK TOP SECRET//NOFORN") | Dihilangkan (DR-11) | luar lingkup |
| F-20 | Weather overlay, Share, MTS/MNF, menu aplikasi | Dihilangkan | luar lingkup |
| F-21 | Legend (kiri bawah peta) | Panel Legend dari rail | ditunda (butuh #10) |
| F-22 | Aksi objek: Add correlation, Analyze track history, Filter out, Share in chat | Aksi analitik dari engine (correlation, track history, filter) | ditunda (butuh #11, #8) |
| F-23 | Heatmap kerapatan event di peta (varian gelap) | Heatmap kerapatan objek | belum ada issue — tunggu data nyata |

### 4.1 Registry nama alat Gaia (issue #4)

Enam nama alat yang disetujui Randy, ditampilkan di tab `Tools` sebagai label presentasional
(tanpa logika, tanpa tab baru, tanpa UI duplikat):

| Nama alat | PRD | Implementasi |
|---|---|---|
| Track & Breadcrumbs | F-16 | #12 |
| Heatmap | F-23 | belum ada issue — tunggu data nyata |
| Routes & Pathways | F-17 (geometri garis dari data) | #10 |
| Draw & Spatial Search | F-18 | ditunda (butuh #10) |
| Time Control | F-14 | #12 |
| Map Layers | F-05 (label saja; manajemen layer tetap di tab `Layers`) | #7 |

## 5. Peta penamaan (referensi → software ini)

| Istilah referensi | Istilah kita |
|---|---|
| Map layers | Layers |
| Data sources | Sources |
| Tools | Tools |
| Selection | Selection |
| Live Entities / SIGINT Notional / Intel Data / Live feed | data demo — tidak dipakai |
| Locations of Interest | Locations of Interest |
| Create Order of Battle layer | Create layer |
| Enemy Unit | Entity type (belum dipakai) |
| CartoDB Light | Basemap (lokal: PMTiles) |
| Map health: Connected | Engine: online / offline |
| 72 interactive elements | Objects: N |
| Live (badge jam) | jam lokal, tanpa badge Live (tidak ada feed langsung) |

## 6. Layout, ukuran, dan token

| Elemen | Ukuran |
|---|---|
| Sidebar workspace | 240 px (expanded) / 56 px (collapsed) |
| Baris navigasi sidebar | 32 px, ikon 16 px, label 12 px |
| Banner klasifikasi | 20 px, teks 11 px uppercase, `emerald-700` |
| Panel Gaia | 248 px, tab 32 px |
| Rail ikon kanan | 36 px, tombol 28 px, ikon 16 px |
| Kanvas peta | sisa ruang: `min-w-0 flex-1`, tinggi penuh, `overflow-hidden` |
| Status bar | 28 px, teks 11 px, `tabular-nums` untuk angka/jam |
| Strip waktu (F-14/F-15) | 28 px (kontrol) + panel histogram 160–200 px saat dibuka |
| Warna aktif | latar `blue-50`, teks `blue-700` |
| Border | 1 px `border-border`; permukaan `bg-background` / `bg-sidebar` |

## 7. Aturan interaksi

- IR-1: satu panel kiri boleh dilipat; state panel dan tab tidak perlu persist antar sesi sampai ada issue yang memintanya.
- IR-2: tab panel mengubah isi panel, bukan route.
- IR-3: seleksi objek membuka panel kanan; tanpa seleksi panel kanan tertutup (rail tetap tampil).
- IR-4: status bar selalu jujur: `Engine: offline` sampai engine benar-benar dipanggil, `Basemap: none` sampai ada file basemap.
- IR-5: semua aksi analitik menampilkan state loading/error dari engine, tidak pernah diam.
- IR-6: peta tidak boleh memicu permintaan jaringan implisit (DR-12).

## 8. Aksesibilitas

- A-1: semua kontrol ikon punya `aria-label`; kontrol disabled tetap punya nama.
- A-2: focus ring terlihat di semua kontrol interaktif (`focus-visible:ring-2`).
- A-3: navigasi memakai elemen semantik (`nav`, `aside`, `main`, `role="toolbar"`).
- A-4: tab panel memakai `aria-pressed`; item navigasi aktif memakai `aria-current="page"`.
- A-5: ukuran baris 28–32 px tetap memenuhi target klik karena kepadatan disengaja (desktop-only, target 24 px+ dengan label/tooltip).

## 9. Arsitektur dan batas tanggung jawab

```
src/          UI Next.js (static export) — tanpa akses filesystem langsung
src-tauri/    shell + jembatan: perintah Rust yang aman (whitelist argumen, timeout)
engine/       Python: analitik, baca configs/ + data/, tulis JSON/GeoJSON ke stdout
database/     schema & migrasi (teknologi belum dipilih)
data/         data lokal: basemap, manifest, turunan (git-ignored)
configs/      sumber, region, analisis (di-commit)
```

- Batas 1: UI tidak membaca file langsung; lewat perintah Tauri.
- Batas 2: UI tidak menyimpan logika analitik; semua di engine.
- Batas 3: engine tanpa state, input dari `configs/`/`data/`, output satu JSON envelope.
- Batas 4: **GitHub Actions adalah satu-satunya runtime backend.** Tidak ada server API, worker, atau
  mode lokal; UI memicu workflow lewat GitHub API dan membaca statusnya (issue #14,
  `docs/backend-runtime.md`).
- Batas 5: tanpa jaringan kecuali fitur menyatakannya (DR-12).
- Batas 6: token GitHub disimpan di keychain OS lewat perintah Tauri; tidak pernah masuk repo, bundle,
  `localStorage`, atau log.

Fondasi ETL engine (kontrak metadata, ingest, transform, SQL, validasi) ada di
`engine/src/geoint_prospect/etl/`, CLI stabilnya di `engine/src/geoint_prospect/cli.py` — rinciannya
di `engine/README.md`.

Dua workflow: `ci.yml` (validasi kode, tanpa kredensial) dan `backend.yml` (`workflow_dispatch` saja,
jalur pekerjaan produksi).

Akuisisi sumber (issue #15) hidup di `geoint_prospect.ingestion` dan hanya menerima `source_id` dari
registry `configs/sources/`; connector melakukan streaming ke staging di runner, mencatat manifest
(checksum, lisensi, provenance), lalu menyerahkan file ke ETL yang sama — tidak ada transformasi ganda
dan tidak ada connector produksi B2/Filebase di dalam engine.

Kontrak engine:

```
python -m geoint_prospect <command> [--json]
→ {"ok": true, "data": ..., "error": null}  |  {"ok": false, "data": null, "error": {"code": "...", "message": "..."}}
```

## 10. Roadmap dan indeks issue

| Issue | Judul | PRD | Prasyarat |
|-------|-------|-----|-----------|
| #1 | Scaffold proyek dan tooling | §2 | — |
| #2 | Sidebar workspace terang | §6, DR-6 | #1 |
| #3 | Chrome workspace Gaia (clone terang) | §4 F-01..F-03, F-09, F-10, F-12 | #2 |
| #4 | Registry nama alat Gaia di tab Tools | §4.1 | #3 |
| #5 | Kanvas MapLibre + status bar nyata | F-07, F-12 | #3 |
| #6 | Basemap lokal (PMTiles) lewat Tauri | F-08 | #5 |
| #7 | Model layer + panel Layers | F-04, F-05 | #5 |
| #8 | Kontrak API engine + katalog sumber/layer | §9 | #1 |
| #9 | Panel Sources lewat jembatan engine | F-13, §9 | #8 |
| #10 | Render fitur layer (GeoJSON) di peta | F-17, F-06 | #7, #8 |
| #11 | Seleksi + panel inspector | F-11, F-22 | #10 |
| #12 | Kontrol waktu: timeline + histogram | F-14, F-15, F-16 | #10 |
| #13 | Fondasi ETL engine (Polars, DuckDB, Arrow, Pydantic, Pandera) | §9 | #1 |
| #14 | Runtime backend di GitHub Actions + pemicu dari desktop | §9, `docs/backend-runtime.md` | #13 |
| #15 | Data ingestion (akuisisi sumber) → ETL di runner yang sama | §9, `configs/sources/README.md` | #13, #14 |

Belum dibuatkan issue (menunggu prasyarat): F-18 editor geometri + simpan ke `database/`, F-21
legend, F-06 pembuatan layer, F-22 aksi analitik, heatmap peta (tunggu data nyata), serta workspace
Browser/Graph/Object Explorer/Dossier dan halaman Settings/System Status yang nyata.

## 11. Di luar lingkup saat ini

Tema gelap dan toggle tema; branding; dashboard; API server; database server; data demo dan feed
langsung; penandaan klasifikasi nyata; bundling installer (`.deb`/AppImage) dan auto-update.
Catatan: pekerjaan backend **bukan** lagi di luar lingkup — sejak issue #14 backend berjalan di
GitHub Actions (job-based, bukan API yang selalu hidup).

## 12. Pertanyaan terbuka

| ID | Pertanyaan | Rekomendasi |
|----|------------|-------------|
| Q-1 | Basemap: file PMTiles lokal di `data/basemaps/` atau style online? | Lokal (offline-first, DR-12). File disediakan Randy. |
| Q-2 | ~~Engine dipanggil bagaimana~~ | **Dijawab (#13/#14):** hanya lewat GitHub Actions, `python -m geoint_prospect` di runner. Tidak ada runtime lokal atau sidecar. |
| Q-3 | Persistensi urutan/visibilitas layer di mana? | Preset repo di `configs/analysis/`; state pengguna di app-config dir Tauri. |
| Q-4 | Format koordinat default? | DD, dengan DMS tersedia di status bar. |
| Q-5 | F-14/F-15/F-16 perlu sekarang atau setelah ada data waktu? | Setelah #10 punya objek bertimestamp. |
| Q-6 | Butuh mode "Live"? | Tidak; status bar menampilkan jumlah objek, bukan feed langsung. |
