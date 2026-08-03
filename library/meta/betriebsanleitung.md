---
type: moc 
status: evergreen 
tags:
- moc
- meta
---

# 📖 Bedienungsanleitung — dein ADHS-Wissensgraph

> **TL;DR — das ganze System sind 3 Bewegungen:**
> 
> 1. **Reinwerfen** → alles zuerst in die Tagesnotiz. Roh, ohne Nachdenken.
> 2. **Verknüpfen** → Gedanken, die bleiben sollen, in `[[Klammern]]` + eine Kante ziehen.
> 3. **Review** → einmal die Woche 10 Min das Dashboard durchgehen.
> 
> Mehr ist es nicht. Alles Weitere ist Kür.

---

## 1 · Der tägliche Kern: Reinwerfen

Die Tagesnotiz ist deine **Inbox**. Kein „wohin damit?" — das ist der ganze Trick gegen die ADHS-Erfassungs-Hürde.

- Tagesnotiz-Icon klicken → heutiges Journal öffnet sich
- Alles rein: Gedanken, Links, halbe Sätze, Fragen
- **Struktur kommt später.** Beim Reinwerfen wird _nicht_ sortiert.

> Faustregel: Wenn du beim Erfassen überlegst „wo gehört das hin?", machst du es falsch. Erst rein, dann (im Review) ordnen.

---

## Basics

Das ist das komplette Bedien-Vokabular. Mehr Handgriffe gibt es nicht.

### ① Aus einem Gedanken ein Atom machen

Gedanken in der Tagesnotiz mit `[[eckigen Klammern]]` umschließen → wird eigene Notiz → reinklicken → **Template einfügen** (Hotkey) → Titel steht schon.

Über: CMD+P

### ② Einen Open Loop festhalten

Eine offene Frage, die dich juckt → neue Notiz → **Open-Loop-Template**. Das externalisiert den Juckreiz und entlastet den Kopf.

### ③ Eine Kante ziehen

Im Text der Notiz tippen: `kantentyp:: [[andere Notiz]]` Beispiel: `tension_with:: [[LLM-as-Judge Kalibrierung]]`


## 3 · Cheat-Sheet

### Knoten-Typen (`type:` + Tag)

|Typ|`type:`|wofür|
|---|---|---|
|Atom|`atom`|eine Idee, die Grundeinheit|
|Open Loop|`open-loop`|offene Frage / der Juckreiz|
|Source|`source`|Buch, Paper, Gespräch|
|Anker|`project` / `person` / `event`|woran Atome andocken|
|Someday|`someday`|Interessens-Spike parken|
|MOC|`moc`|Themen-Hub / Wiedereinstieg|

### Kanten-Typen (Inline `::` im Text)

|Syntax|Bedeutung|
|---|---|
|`relates_to::`|genereller Fallback (wenn kein Typ passt)|
|`supports::`|stützt / ist Beispiel für|
|`tension_with::`|steht in Spannung / widerspricht|
|`reminds_me_of::`|rein assoziativ|
|`leads_to::`|Reihenfolge / Voraussetzung|
|`blocked_by::`|hängt an etwas fest|

### Properties (Frontmatter, alle optional außer `type`/`tags`)

|Feld|Werte|Zweck|
|---|---|---|
|`status`|inbox → developing → evergreen → archived|Reifegrad|
|`energy`|low / med / high|Match an deinen Zustand|
|`interest`|low / med / high|wie dopaminerg = gehst du dran?|
|`context`|@computer / @phone / @errand|wo erledigbar|

---

## 4 · Das Dashboard lesen (`00-…Setup`, Teil 5)

Öffne das Setup-MOC in der **Leseansicht**. Jede Query sagt dir eine Sache — und was zu tun ist:

|Query|Sagt dir…|Deine Aktion|
|---|---|---|
|**Open-Loop**|welche Fragen offen sind|eine beantworten oder auf `resolved` setzen|
|**Orphans**|welche Atome einsam sind|ein, zwei Kanten ziehen|
|**Spaced Resurfacing**|was du lang nicht sahst|kurz lesen, ggf. ergänzen|
|**Energy-Match**|was JETZT bei wenig Kraft geht|ein Inbox-Item wegräumen|
|**Tension-Map**|wo Ideen sich reiben|nachdenken — hier steckt Erkenntnis|
|**Inbox**|was noch Struktur braucht|`status` geben oder Kante ziehen|

---

## 5 · Der wöchentliche 10-Minuten-Durchlauf ⭐

Das ist dein **komplettes Wartungssystem**. Kein tägliches Pflegen nötig.

1. Setup-MOC → Leseansicht
2. **Inbox-Query** durch → jedem Eintrag `status` geben _oder_ eine Kante
3. **Orphan-Query** → 1–2 einsame Atome verbinden
4. **Open-Loop-Query** → was ist gelöst? was juckt noch?
5. Fertig. Zumachen.

> Timer auf 10 Min. Wenn er klingelt, hörst du auf — auch wenn nicht „alles" erledigt ist. Ein unperfektes wöchentliches Review schlägt ein perfektes, das nie stattfindet.

---

## 6 · Bedien-Prinzipien

- **Capture-first.** Erst rein, dann ordnen. Immer.
- **Felder dürfen leer sein.** Beim Erfassen zählt nur `type` + `tags`. `energy`/`interest` sind Kür fürs Review.
- **Wöchentlich, nicht täglich.** Das System ist auf einen Wochen-Rhythmus gebaut. Tägliches Pflegen ist nicht vorgesehen und wäre Reibung.
- **Ein Tastendruck genügt.** Template-Hotkey statt Tippen.
- **`relates_to` ist immer erlaubt.** Wenn du den Kantentyp nicht entscheiden willst → `relates_to::`. Nie an der Typ-Wahl hängenbleiben.
- **Nicht ausbauen, bis es zwickt.** Farben, Breadcrumbs, mehr Typen — erst wenn du den Mangel _spürst_.

---

## 7 · Tastenkürzel (empfohlen)

Unter **Einstellungen → Tastenkürzel** vergeben:

|Aktion|Vorschlag|
|---|---|
|Vorlage einfügen|Strg+Alt+T|
|Neue Notiz|Strg+N (Standard)|
|Zur Tagesnotiz|Strg+Alt+D|
|Schnellsuche|Strg+O (Standard)|

---

## 8 · Wann ausbauen? (erst später)

- **Farben wie im Schematic** → `graph.css` + Juggl. Reiner Dopamin-Bonus.
- **Kanten traversieren** → Breadcrumbs (`00-…Setup`, Teil 6). Nur wenn du wirklich durch Typen navigieren willst.
- **Auto-Properties** → Templater. Nur wenn dich der eine Template-Tastendruck nachweislich nervt.

Alle drei sind **optional** und stehen bereit. Kein Muss.

---

> **Merksatz:** Das _genutzte_ mittelmäßige System schlägt das _perfekte, ungenutzte_ — jedes Mal. Dein System läuft ab jetzt. Benutz es zwei Wochen, dann bau gezielt aus, was dich echt bremst.