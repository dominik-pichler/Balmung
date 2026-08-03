---
type: moc
status: evergreen
tags:
  - moc
  - meta
---


# Schema

### Node-Typen → `type` in der Frontmatter + Tag

| Ontologie-Knoten | `type:` | Tag |
|---|---|---|
| Atom | `atom` | `#atom` |
| Open Loop | `open-loop` | `#open-loop` |
| Source | `source` | `#source` |
| Person / Projekt / Event | `person` / `project` / `event` | `#anchor` |
| Someday / Maybe | `someday` | `#someday` |
| MOC | `moc` | `#moc` |

### Kanten-Typen → Inline-Felder (`::`) im Fließtext

Die schreibst du **da, wo du eh tippst** — mitten im Satz. Der Key *ist* das Label.

| Ontologie-Kante | Obsidian-Syntax |
|---|---|
| `supports` / `example_of` / `part_of` | `supports:: [[Notiz]]` |
| `relates_to` (der Fallback ohne Typ-Entscheidung) | `relates_to:: [[Notiz]]` |
| `tension_with` / `contradicts` | `tension_with:: [[Notiz]]` |
| `reminds_me_of` (assoziativ) | `reminds_me_of:: [[Notiz]]` |
| `leads_to` / `prerequisite_for` | `leads_to:: [[Notiz]]` |
| `blocks` / `blocked_by` | `blocked_by:: [[Notiz]]` |

**Warum Inline und nicht Frontmatter?** Weil die Beziehung im Kontext steht: „…das widerspricht `tension_with:: [[LLM-as-Judge Kalibrierung]]` weil…". Node-Metadaten hingegen gehören nach oben in die Properties.

### Properties → Frontmatter (YAML)

```yaml
---
type: atom
status: inbox        # inbox → developing → evergreen → archived
energy: med          # low / med / high  → match an deinen Zustand
interest: high       # wie dopaminerg → prognostiziert, ob du drangehst
context: "@computer" # @computer / @phone / @errand
tags:
  - atom
---
```

> **ADHS-Trick:** Kein `last_touched`-Feld pflegen! Obsidian trackt `file.mtime` automatisch. Manuelle Datumsfelder = Reibung = du machst es nicht.

---

## Teil 3 · Templates

**Settings → Templates → Template folder location** = z.B. `_templates`. Dann pro Typ eine Vorlage anlegen. Einfügen per Hotkey (`Insert template`).

### `_templates/Atom.md`

```
---
type: atom
status: inbox
energy: med
interest:
tags:
  - atom
---

# {{title}}


<!-- Kanten (löschen, was du nicht brauchst): -->
relates_to::
supports::
tension_with::
```

### `_templates/Open-Loop.md`

```
---
type: open-loop
status: open
energy:
tags:
  - open-loop
---

# ❓ {{title}}

**Die Frage:**

**Warum es juckt:**


relates_to::
tension_with::
```

---

## Teil 4 · Der Erfassungs-Workflow (capture-first)

1. **Tagesnotiz = Inbox.** App auf → du bist im heutigen Journal. Alles fliegt hier rein, roh, ohne „wohin damit?".
2. Ein Gedanke, der bleiben soll → `[[eckige Klammern]]` drum → wird zum Atom (`status: inbox`).
3. **Struktur asynchron:** Später (z.B. Wochen-Review, 10 Min) gehst du die Inbox-Query durch und ziehst Kanten. Nicht beim Erfassen.

Das ist der ganze Punkt: **rohes rein, Struktur später (oder nie).**

---

## Teil 5 · Die Queries = dein Dashboard

Sobald diese Notiz im Vault liegt (mit Dataview aktiv), sind die Blöcke unten **live**. Das ist dein Wiedereinstiegs-Cockpit.

### 🔴 Open-Loop-Resurfacing — offene Fragen, älteste zuerst

```dataview
TABLE status, energy, dateformat(file.mtime, "dd.MM.yyyy") AS "Zuletzt"
FROM #open-loop
WHERE status != "resolved"
SORT file.mtime ASC
LIMIT 10
```

### 🌱 Spaced Resurfacing — Evergreens, die du >30 Tage nicht berührt hast

```dataview
TABLE interest, dateformat(file.mtime, "dd.MM.yyyy") AS "Zuletzt"
FROM #atom
WHERE status = "evergreen" AND file.mtime < date(today) - dur(30 days)
SORT file.mtime ASC
LIMIT 5
```

### 🔌 Orphan Detection — Atome ohne jede Verbindung (brauchen Integration)

```dataview
TABLE dateformat(file.ctime, "dd.MM.yyyy") AS "Erstellt"
FROM #atom
WHERE length(file.inlinks) = 0 AND length(file.outlinks) = 0
SORT file.ctime ASC
```

### ⚡ Energy-Match — was du JETZT bei wenig Energie wegräumen kannst

```dataview
TABLE type, context
WHERE energy = "low" AND status = "inbox"
LIMIT 15
```

### ⚔️ Tension-Map — alle dialektischen Spannungen auf einen Blick

```dataview
TABLE tension_with AS "steht in Spannung zu"
WHERE tension_with
```

### 📥 Inbox-Aufräumen — was noch Struktur braucht

```dataview
TABLE type, dateformat(file.ctime, "dd.MM.yyyy") AS "Erstellt"
WHERE status = "inbox"
SORT file.ctime ASC
```

---

## Teil 6 · Breadcrumbs (der *echte* getypte Graph) — optional

Wenn dir die Query-Sicht nicht reicht und du Kanten *traversieren* willst:

1. Breadcrumbs installieren.
2. **Settings → Breadcrumbs → Edge Fields:** deine Kanten-Typen als Felder registrieren (`supports`, `relates_to`, `tension_with`, …). Damit erkennt Breadcrumbs deine `feld:: [[link]]`-Inline-Syntax als echte getypte Kante.
3. Views nutzen (Matrix / Tree), um dich entlang der Typen durch den Graphen zu hangeln.

> ⚠️ Breadcrumbs 4.x hat die Konfig gegenüber älteren Versionen umgebaut — die genauen UI-Bezeichnungen können abweichen. Im Zweifel kurz in die Breadcrumbs-Docs schauen, das Konzept (Edge Fields registrieren) bleibt gleich.

---

## Teil 7 · Juggl (Kanten *mit Labels sehen*) — optional/advanced

Das ist die Live-Version deines SVG-Schematics:

1. Juggl installieren (zieht Breadcrumbs-Kanten automatisch mit ein).
2. Auf einer Notiz → „more options" → **Open Juggl workspace**.
3. Über den **Style Pane** Knoten nach `type` einfärben (Atom = Mint, Open Loop = Magenta, …) und Kanten-Labels anzeigen.

> Juggl ist mächtig, aber gelegentlich zickig — deshalb hier ganz unten. Der Wert liegt zu 80 % schon in Teil 1–5. Juggl ist Dopamin-Bonus, kein Fundament.

---