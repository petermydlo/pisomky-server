# Používateľská príručka — Písomkový server (pisomky)

Táto príručka je určená **učiteľovi**, ktorý appku používa na tvorbu a vyhodnocovanie
školských testov. Nie je to technická dokumentácia pre vývojárov — cieľom je, aby si
učiteľ, ktorý appku dlhšie nepoužíval, vedel podľa tohto textu spomenúť/naučiť sa
všetky funkcie systému.

---

## 1. Úvod

Písomkový server umožňuje:

- spravovať databázu otázok rozdelenú podľa predmetov, kapitol a kategórií,
- vygenerovať sadu testov pre triedu/skupinu (každému žiakovi iný, náhodne
  poskladaný test s jedinečným kľúčom),
- zdieľať test so žiakmi (žiak zadá kľúč do formulára a vyplní test v prehliadači),
- zbierať odpovede žiakov (aj z papierových testov cez fotku/sken, pomocou AI),
- opravovať a bodovať odpovede (ručne aj s pomocou AI pre otvorené otázky),
- poskytovať žiakom AI nápovedu počas písania testu,
- exportovať testy, výsledky a QR kódy do PDF,
- zobraziť štatistiky úspešnosti skupiny a jednotlivých otázok.

Základné pojmy:

| Pojem | Význam |
|---|---|
| **predmet** | skratka predmetu, napr. `PIT4`, `SXT4`, `AUT3` — zodpovedá adresáru v `res/xml/questions/` |
| **kapitola** | tematický celok v rámci predmetu (napr. `01`, `c03`), obsahuje kategórie |
| **kategória** | skupina otázok, z ktorej sa pri generovaní testu vyberie určený `pocet` otázok |
| **otázka** | jednotlivá otázka — buď s výberom odpovede (MCQ), alebo otvorená (text/príkaz) |
| **kľúč testu** (`kluc`) | jedinečný identifikátor jedného vygenerovaného testu pre jedného žiaka — žiak ho zadáva na úvodnej stránke |
| **skupina** | podskupina triedy (napr. `pit1`, `pit2`) — testy sa dajú generovať pre celú triedu alebo len pre skupinu |
| **fileid** | krátky identifikátor konkrétneho behu generovania (odlišuje viac vygenerovaní tej istej kombinácie predmet/trieda/kapitola) |
| **sedenie** | voliteľný údaj o mieste žiaka v učebni (riadok+stĺpec), používaný pri "sedenie-vedomom" generovaní proti odpisovaniu |

---

## 2. Prihlásenie / autentifikácia

Appka nemá vlastný prihlasovací formulár. Admin časť (`/admin` a všetky jej
podstránky) je chránená hlavičkou `X-Remote-User`, ktorú nastavuje reverse proxy
(HTTP Basic Auth na úrovni nginx). Meno prihláseného učiteľa (`X-Remote-User`) sa
používa ako hodnota atribútu `autor` pri vytváraní testov, kategórií aj otázok —
učiteľ tak v prehľade (`/admin`) vidí len svoje vlastné testy (plus tie bez
priradeného autora).

**Odhlásenie**: appka nemá tlačidlo odhlásiť sa v klasickom zmysle. Na stránke
`/admin` je meno prihláseného učiteľa zobrazené ako klikateľný text (`<span
class="autor">`) v hlavičke každého predmetu. Klik naň pošle požiadavku s neplatnými
Basic Auth údajmi, čím prehliadač zneplatní uložené prihlásenie — po kliknutí sa
zobrazí upozornenie *"Na odhlásenie, prosím, zatvorte toto okno prehliadača."* Ak
prehliadač požiadavku odmietne, appka rovno presmeruje na úvodnú stránku. Skutočné
odhlásenie teda vyžaduje zatvorenie okna/karty prehliadača (typické správanie HTTP
Basic Auth).

---

## 3. Správa zoznamu žiakov (`roster.xml`)

Zoznam tried a žiakov je súbor `res/xml/lists/roster.xml`. Nemá vlastný formulár v
appke — upravuje sa priamo ako XML súbor (napr. pri prijatí novej triedy). Nemá ani
XSD schému, jeho štruktúra je nasledovná:

**Koreňový element `<triedy xml:lang="sk">`** obsahuje ľubovoľný počet `<trieda>`.

**`<trieda>`** — povinné:
- `id` — názov triedy (napr. `III.C`), presne tak, ako sa má zobraziť pri generovaní testu

**`<student>`** — povinné:
- `meno`
- `priezvisko`

Voliteľné atribúty `<student>`:
- `skupina` — do akej skupiny/skupín žiak patrí (voliteľné; môže byť aj zoznam
  oddelený čiarkou, napr. pri delení na viac krúžkov naraz); ak chýba, žiak patrí len
  do "celej triedy"
- `sedenie` — pozícia žiaka v učebni vo formáte `"1A"` = `<riadok><stĺpec>` (napr.
  `1A`, `2B`, `3C`...). Používa sa výhradne pri generovaní testov s **anti-odpisovacím
  algoritmom**: žiaci majú priradené miesto (rad + stĺpec) a systém pri generovaní
  zaručí, že žiak nedostane rovnakú otázku/vetvu/alternatívu ako jeho priamy sused v
  rade alebo predo/za ním. Žiaci bez `sedenie` sa generujú nezávisle ako doteraz.

Príklad (skrátený):

```xml
<?xml version="1.1" encoding="UTF-8"?>
<triedy xml:lang="sk">
   <trieda id="III.C">
      <student meno="Marko" priezvisko="Auxt" skupina="een"/>
      <student meno="Damian" priezvisko="Dilik" skupina="pit1" sedenie="1A"/>
      <student meno="Ondrej" priezvisko="Dimoš" skupina="pit1" sedenie="1B"/>
   </trieda>
</triedy>
```

Pri generovaní testu (formulár "Vytvorenie nového testu") sa zoznam tried a skupín
čerpá priamo z tohto súboru.

---

## 4. Správa otázok a kategórií

### 4.1 Kde a ako

Editor otázok je na `/admin/selectquestions` (ikona ceruzky "Edit questions" v
hornej lište `/admin`). Po výbere predmetu (`POST /admin/showquestions`) sa zobrazí
zoznam kapitol → kategórií → otázok daného predmetu, spolu so štatistikou úspešnosti
(percento správnych odpovedí za otázku/kategóriu/kapitolu, ak už existujú odpovede).

Kapitoly, kategórie aj otázky sa dajú priamo v tomto prehľade aj pridávať, upravovať,
mazať a obnovovať — ikony (➕ pridať, ✎ upraviť, 🗑 zmazať, ↺ obnoviť) sa zobrazia po
prejdení myšou nad príslušným riadkom. Netreba teda meniť XML súbory ručne.

Otázky, kategórie aj kapitoly majú stabilné `id` — 8-znakový hexadecimálny hash
(SHA-256), ktorý sa dopĺňa automaticky pri prvom použití súboru (funkcia
`ensure_ids`), učiteľ ho nezadáva ručne.

### 4.2 Kapitoly

Vytvorenie/premenovanie/vymazanie cez `POST /admin/process_chapter`
(`operacia=create|update|delete`). Nová kapitola vytvorí nový XML súbor
`res/xml/questions/{predmet}/{predmet}_{kapitola_id}.xml`. `operacia=update` mení
len `nazov`. Vymazanie kapitoly je možné len ak jej otázky ešte neboli použité v
žiadnom teste — kapitola nemá "archivovaný" stav ako kategória/otázka (mazacia
ikona je v editore v takom prípade zobrazená ako neaktívna).

### 4.3 Kategórie

Vytváranie/úprava/mazanie/obnova cez `POST /admin/process_category`:
- `operacia=create` — vyžaduje `kapitola_id`; voliteľne `za_kategoria_id` (za ktorú
  kategóriu vložiť), `pocet`, `body`, `static`, `bonus`, `nazov`
- `operacia=update` — mení `pocet`, `body`, `static`, `bonus`, `nazov`
- `operacia=delete` — ak je niektorá otázka kategórie použitá v teste, **nemaže sa
  fyzicky**, len sa nastaví `deprecated="1"` na kategórii (nie na jej otázkach)
- `operacia=restore` — odstráni `deprecated` z kategórie (nerobí nič s jej otázkami)

Atribúty kategórie (XSD `questions.xsd`, typ `Kategoria`):

**Povinné:**
- `id` — hash
- `pocet` — koľko otázok sa z kategórie náhodne vyberie do testu

**Voliteľné:**
- `body` — počet bodov za otázky z kategórie (ak sa nezadáva na úrovni otázky)
- `nazov` — čitateľný názov kategórie (inak sa zobrazuje `id`)
- `deprecated="1"` — kategória vyradená z používania (nemaže sa fyzicky, ak je
  referencovaná v existujúcich testoch)
- `paused="1"` — kategória dočasne pozastavená (nebude sa žrebovať do nových testov,
  dá sa prepínať priamo v editore cez checkbox pri kategórii)
- `static="1"` — kategória sa neskladá náhodne, do testu ide vždy celá (typicky pre
  úvodné/spoločné úlohy)
- `bonus="1"` — bonusová kategória, body sa nezapočítavajú do maxima, len sa pridávajú navyše
- `autor` — meno učiteľa vlastniaceho kategóriu
- `nahrada_za` — id kategórie, ktorú táto nahrádza (pre daného autora)

### 4.4 Otázky

Vytváranie/úprava/mazanie/obnova cez `POST /admin/process_question`:
- `operacia=create` — vyžaduje `kategoria_id`; voliteľne `za_otazka_id`, `znenie`,
  `body`, `static`, `bonus`, `nazov`, `vzor`, `klucove_slova` (JSON pole), `odpovede` (JSON
  pole objektov `{text, spravna, napovedy}`), `napovede` (JSON pole textov
  celoplošných nápovedí)
- `operacia=update` — mení tie isté polia. Ak je otázka **použitá** v existujúcom
  teste a mení sa čokoľvek okrem `vzor`/`klucove_slova`/nápovedí/`nazov` (teda `znenie`,
  `odpovede`, `body`, `static`, `bonus`), appka **automaticky namiesto zápisu na
  mieste vytvorí novú otázku** (aby sa neskombinovali štatistiky starej a novej
  verzie pod jedným `id`) — pôvodná otázka dostane `deprecated="1"`, nová je úplne
  samostatná (žiadna väzba medzi nimi v XML). Toto rozhodnutie robí server sám,
  učiteľ v editore len uloží zmeny bežným spôsobom.
- `operacia=delete` — ak je otázka použitá v existujúcom teste, **nemaže sa fyzicky**,
  len sa nastaví `deprecated="1"` (viď `AGENTS.md` sekcia "Forbidden")
- `operacia=restore` — odstráni `deprecated` z otázky (nerobí nič s jej kategóriou)

Surové dáta otázky pre editačný formulár (znenie, odpovede aj s nápoveďami, vzor,
kľúčové slová) vracia `GET /admin/question?id=...`; pre kategóriu `GET
/admin/category?id=...`. Či je kategória/otázka použitá v teste (pre text
potvrdzovacieho dialógu pri mazaní) zisťuje `GET /admin/is_used?id=...&typ=kategoria|otazka`.

Otázka podporuje dva základné typy:
1. **Výberová (MCQ)** — obsahuje viacero `<odpoved>`, každá s atribútom `spravna="0"`
   alebo `"1"` (jedna alebo viac môže byť správna).
2. **Otvorená otázka** — bez `<odpoved>`, ale s `<vzor>` (vzorová odpoveď), voliteľne
   `klucove_slova` (kľúčové slová pre AI hodnotenie) — pozri kapitolu 10 (AI hodnotenie).

Atribúty a elementy otázky (`questions.xsd`, typ `Otazka`):

**Povinné:**
- `id` — hash
- aspoň jeden `<znenie>` (text zadania — hoci XSD ho formálne označuje ako voliteľné
  v rámci `xs:choice`, v praxi má každá zmysluplná otázka `<znenie>`)

**Voliteľné atribúty:**
- `deprecated="1"` — vyradená otázka (viď vyššie)
- `paused="1"` — dočasne pozastavená (nebude sa žrebovať)
- `static="1"` — otázka sa do testu zaraďuje vždy (nie je súčasťou náhodného výberu
  v rámci kategórie)
- `body` — počet bodov
- `nazov` — čitateľný názov otázky (inak sa v editore zobrazuje `id`)
- `pomer` — napr. `"1:4"`, pomer pre čiastočné bodovanie (partial scoring)
- `rating` — voliteľné hodnotenie/váha
- `cesta` — čiarkou oddelené identifikátory "vetiev" (používa sa pri delení otázok
  do variantov A/B a pod. — pozri príklad SXT4 nižšie)
- `bonus="1"` — bonusová otázka, body sa nezapočítavajú do maxima, len sa pridávajú navyše
- `autor` — meno učiteľa (smie byť prítomné len spolu s `nahrada_za`)
- `nahrada_za` — id otázky, ktorú táto nahrádza (pre daného autora)

**Voliteľné vnorené elementy:**
- `<odpoved spravna="0|1" napoveda_key="...">text</odpoved>` — jedna z možností pri
  MCQ; atribút `napoveda_key` je id tejto odpovede, na ktoré odkazujú `<napoveda pre="...">`
  elementy otázky (viď nižšie) — nie je to samotný text nápovedy
- `<vzor>text</vzor>` — vzorová odpoveď pre otvorenú otázku (používa sa aj pri AI
  hodnotení a AI nápovede); podporuje zástupné symboly `{meno}`, `{priezvisko:low
  rep}` a pod. (nahradia sa údajmi žiaka pri AI hodnotení)
- `<napoveda pre="...">text</napoveda>` — nápoveda k otázke, môže sa opakovať
  (jedna otázka môže mať ľubovoľne veľa `<napoveda>` elementov):
  - bez `pre` — celoplošná, platí vždy, nezávisle od zvolenej odpovede
  - s `pre="id"` — zobrazí sa len keď žiak zvolí odpoveď, ktorej `napoveda_key`
    sa rovná tomuto `id`. **Jedna odpoveď môže mať aj viac nápovedí naraz** —
    stačí pridať viac `<napoveda pre="rovnaké id">` elementov, všetky sa
    priradia k tej istej odpovedi (netreba nič spájať do jedného atribútu)
- `<klucove_slova><slovo>text</slovo>...</klucove_slova>` — kľúčové slová pre
  otvorenú otázku, používajú sa pri AI hodnotení a AI nápovede (pozri kapitolu 10).
  Napríklad:

  ```xml
  <klucove_slova>
     <slovo>premenná</slovo>
     <slovo>dátový typ</slovo>
     <slovo>inicializácia</slovo>
  </klucove_slova>
  ```

Text v `<znenie>` a `<odpoved>` podporuje formátovacie inline elementy: `<italic>`,
`<underline>`, `<bold>`, `<sub>` (dolný index), `<upp>` (veľké písmená), `<alter>`
(alternatívna formulácia, vykreslí sa náhodne jedna z viacerých `<choice>`),
`<placeholder typ="..." transform="..."/>` (zástupný symbol, napr. meno žiaka),
`<obrazok src="..." alt="..." vyska="..."/>`, `<file src="..." nazov="..."/>`,
`<ref id="..."/>` (odkaz na inú otázku podľa jej `id`).

**Príklad — otvorená (praktická) otázka s placeholderom a vzorom** (z reálnych dát,
`res/xml/questions/SXT4/SXT4_c03.xml`):

```xml
<kategoria static="1" pocet="1" body="10" nazov="Názov počítača" id="ba77164d">
   <otazka id="bf46a798">
      <znenie>Pomenujte svoj pocitac <italic>
            <placeholder typ="priezvisko" transform="low rep"/>-server</italic>.</znenie>
      <vzor>sudo hostnamectl set-hostname {priezvisko:low rep}-server</vzor>
   </otazka>
</kategoria>
```

**Príklad — otázka rozdelená do dvoch vetiev (`cesta`)**, s nápoveďou:

```xml
<kategoria pocet="1" body="5" nazov="Pravidlá NFT" id="f2680f52">
   <otazka cesta="A" id="8cc8bdf3">
      <znenie>Povoľte prístup z rozsahu IP 10.20.15.10 až 10.20.15.30 na port 80.</znenie>
      <napoveda>Uuu, is that a contiguous range?</napoveda>
      <vzor>sudo nft add rule inet skuskova dropujuci ip saddr 10.20.15.10-10.20.15.30 tcp dport 80 accept</vzor>
   </otazka>
   <otazka cesta="B" id="d967500e">
      <znenie>Zakážte prístup z rozsahu IP 10.20.15.10 až 10.20.15.30 na port 80.</znenie>
      <napoveda>Uuu, is that a contiguous range?</napoveda>
      <vzor>sudo nft add rule inet skuskova akceptujuci ip saddr 10.20.15.10-10.20.15.30 tcp dport 80 drop</vzor>
   </otazka>
</kategoria>
```

**Príklad — MCQ otázka** (`res/xml/tests/DEMO/...`):

```xml
<otazka id="otq00001" body="1">
   <znenie>Aký je výsledok výrazu 2 + 2?</znenie>
   <odpoved spravna="1">4</odpoved>
   <odpoved spravna="0">3</odpoved>
   <odpoved spravna="0">5</odpoved>
   <odpoved spravna="0">22</odpoved>
</otazka>
```

**Náhodná (`alter`) otázka** (`res/xml/questions/PIT4/PIT4_c01.xml`):

```xml
<otazka static="1" id="0b9ea41c">
   <znenie>1. sínusovka a kosínusovka: <alter>
         <choice>1</choice>
         <choice>2</choice>
         <choice>3</choice>
      </alter>+<alter>
         <choice>1</choice>
         <choice>2</choice>
      </alter>i; ...
   </znenie>
</otazka>
```

Kapitola môže mať aj `<pokyny>` s voliteľným `<head>` (úvodný text pred otázkami) a
`<tail>` (záverečný text), napr. inštrukcie k odovzdaniu.

### 4.5 Pozastavenie kategórie/otázky priamo v editore

V editore otázok (`/admin/showquestions`) je pri každej kategórii a otázke checkbox
na pozastavenie — volá `POST /admin/setpaused` (`typ=kategoria|otazka`,
`paused=1|0`). Pozastavená kategória/otázka sa nebude žrebovať do nových testov, ale
zostáva v databáze (na rozdiel od `deprecated`, ktoré je nevratné/trvalé
označenie nahradenej otázky).

---

## 5. Generovanie testov

### 5.1 Formulár

`GET /admin/selectcreate` zobrazí formulár (ikona "+" v `/admin`): výber predmetu,
triedy (multi-select, viac tried naraz), skupiny (celá trieda alebo konkrétna
skupina napr. `pit1`), kapitoly, voliteľne dátum/čas začiatku a konca písania
(`start`/`stop`), a dva prepínače:
- **Anonymné** — test nespáruje otázky s konkrétnym žiakom podľa mena (žiacky test
  nemá vopred vyplnené meno/priezvisko)
- **Identita** — vyžaduje vyplnenie identity žiaka

### 5.2 `POST /admin/createtests`

Vygeneruje sadu testov (jeden `<test>` element na žiaka) do
`res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml`, kde
`fileid` je náhodný 4-znakový hex identifikátor pridelený automaticky pri vytvorení.
Pre každú vybranú triedu prejde zoznam žiakov z `roster.xml`, pre každého žiaka
vyžrebuje otázky z vybraných kategórií podľa `pocet` a `static`/`bonus` pravidiel.

**Anti-odpisovacie generovanie podľa "sedenia"**: ak majú žiaci v `roster.xml`
vyplnený atribút `sedenie` (napr. `1A`, `1B`...), generátor zaručí, že susedný žiak v
rade (vľavo/vpravo) aj žiak priamo pred/za ním v stĺpci **nedostane rovnakú otázku,
rovnakú `alter`-vetvu ani rovnaký `cesta`-výber** — teda susedia na susedných
laviciach nevidia rovnaké zadanie. Žiaci bez `sedenie` sa žrebujú nezávisle, tak ako
doteraz.

### 5.3 `POST /admin/regeneratetests`

Znovu vygeneruje (prežrebuje) už existujúci súbor testov (rovnaký `fileid`) — vhodné
napr. keď učiteľ zistí chybu v zadaní ešte pred písaním. V prehľade (`/admin`) je
tlačidlo dostupné len pokiaľ ešte **neexistujú žiadne odovzdané odpovede** k danému
súboru (inak je "Regenerate" v UI zablokované — text "Cannot regenerate — answers
exist"). Regenerácia znovu použije pôvodne uložené `sedenie`/`cesta`/`otazka
id`/`alter-vyber` priamo zo starých `<test>` elementov (nepotrebuje znova čítať
`roster.xml`).

### 5.4 Mazanie súboru testov

`DELETE /admin/deletetests` — vymaže súbor testov a voliteľne aj priradený súbor
odpovedí (`del_answers`) a AI feedback (`del_feedback`). V prehľade zodpovedá ikone
"Delete tests" (mínus v štvorčeku).

### 5.5 Zmena časového okna

- `POST /admin/changetime` — nastaví/zmení `start`/`stop` pre celú sadu testov, alebo
  (ak sa zadá aj `kluc`) len pre jedného konkrétneho žiaka (napr. predĺženie času pri
  neskoršom príchode).
- `POST /stoptime/{kluc}` — nastaví čas ukončenia priamo pri odovzdávaní (interné
  volanie appky, keď žiak klikne "odovzdať").

### 5.6 XSD štruktúra `tests.xsd`

Koreňový element `<testy>`. **Povinné atribúty**: `predmet`, `trieda`, `skupina`,
`kapitola`, `gendat` (dátum a čas vygenerovania). **Voliteľné**: `fileid`,
`start`/`stop` (čas písania), `autor`, `identita`, `anonymne`.

Element `<test>` (jeden žiak) — **povinné**: `id` (kľúč testu). **Voliteľné**:
`uuid`, `meno`, `priezvisko`, `trieda`, `start`/`stop` (individuálny čas, ak sa líši
od spoločného), `sedenie` (miesto žiaka v učebni, napr. `"1A"` — prítomné len pri
sedenie-vedomom generovaní, pozri kapitolu 5), `cesta` (zvolená vetva/variant
zadania pre tohto žiaka).

Element `<otazka>` v teste — **povinné**: `id`. **Voliteľné**: `body`, `static`,
`bonus`, `rating`, `alter-vyber` (interná stopa zvolenej pozície `<alter>` v znení,
zapisuje ju generátor pri sedenie-vedomom generovaní kvôli susedskému vylučovaniu —
neupravuje sa ručne), vnorené `<znenie>` a ľubovoľný počet `<odpoved spravna="0|1">`
(chýbajú pri otvorenej otázke).

Príklad (skrátený, `res/xml/tests/DEMO/DEMO_I.A_01_1234.example.xml`):

```xml
<?xml version='1.1' encoding='UTF-8'?>
<testy xml:lang="sk" predmet="DEMO" trieda="I.A" skupina="" kapitola="01" fileid="1234"
       gendat="2025-01-01T10:00:00" start="2025-01-08T09:00" stop="2025-01-08T09:45" autor="ucitel">
   <test uuid="00000000-0000-0000-0000-000000000001" id="demo01xnovaka" meno="Ján" priezvisko="Novák" trieda="I.A">
      <otazka id="otq00001" body="1">
         <znenie>Aký je výsledok výrazu 2 + 2?</znenie>
         <odpoved spravna="1">4</odpoved>
         <odpoved spravna="0">3</odpoved>
         <odpoved spravna="0">5</odpoved>
         <odpoved spravna="0">22</odpoved>
      </otazka>
   </test>
</testy>
```

---

## 6. Zdieľanie testu so žiakmi

Každý žiak dostane svoj vlastný **kľúč** (`<test id="...">`) — buď oznámením (napr.
prečítaním), vytlačením (pozri kapitolu 12 — QR kódy a papierové testy), alebo iným
kanálom. Žiak zadá kľúč na úvodnej stránke appky (`/`) do poľa "Kľúč písomky" a
klikne "Vstúpiť" — appka ho presmeruje na `GET /{kluc}`.

Voliteľné zaškrtávacie pole **"Editovateľný"** na úvodnej stránke zodpovedá query
parametru `?edit=true` — zobrazí formulár na vypĺňanie (`writetest.xsl`) namiesto
len náhľadu zadania (`showtest.xsl`). V praxi ho žiak zaškrtáva pri vstupe do testu,
aby mohol rovno písať.

Učiteľ môže rovnaký test zobraziť v admin režime cez `GET /admin/{kluc}` — vidí
zadanie aj s administrátorskými právami bez ohľadu na to, či test ešte beží.

---

## 7. Vypĺňanie a odovzdávanie odpovedí (žiacky pohľad)

Vo formulári testu (`writetest.xsl`) žiak vidí:
- pri MCQ otázkach: prepínače (radio) s možnosťami a-d,
- pri otvorených otázkach: textové pole,
- pri praktických (počítačových) otázkach: možnosť nahrať súbor (`<input type="file"
  name="files" multiple="true"/>`),
- pri každej otázke tlačidlo na **AI nápovedu** (pozri kapitolu 9),
- odpočet zostávajúceho času, ak je nastavený `stop`.

Odovzdanie odpovedí ide na `POST /saveanswers/{kluc}` — appka:
1. skontroluje, či test ešte beží (`check_time`), inak vráti chybu 403 "Test už skončil!",
2. uloží prípadné nahrané súbory do `res/xml/answers/{predmet}/{...}_{kluc}-{názov}_subor`,
3. zapíše textové odpovede do XML súboru odpovedí (vytvorí ho, ak ešte neexistuje).

Opakované odoslanie (napr. žiak stihne poslať znova pred koncom času) prepíše
predchádzajúci pokus (aktualizuje `<test id=kluc>` s novým `dat`). Ak žiak pošle
prázdny formulár po tom, čo už predtým odpovede odoslal, appka len aktualizuje
dátum, aby sa nestratili predošlé odpovede.

### XSD štruktúra `answers.xsd`

Koreňový element `<odpovede>` — **povinné**: `predmet`, `trieda`, `skupina`,
`kapitola`, `fileid`. **Voliteľné**: `autor`.

Element `<test>` (jeden pokus) — **povinné**: `id` (kľúč), `dat` (dátum a čas
odovzdania, ISO 8601).

Element `<otazka>` — **povinné**: `id`; textový obsah = odpoveď žiaka (napr. písmeno
`a`/`b`, alebo voľný text/príkaz pri otvorenej otázke). **Voliteľné**: `body`
(pridelené body pri ručnom hodnotení, pozri kapitolu 10), `koment` (poznámka
učiteľa k oprave) — obidva dopĺňa `/admin/savemarks` až pri opravovaní, v čerstvo
odovzdanej odpovedi ešte nie sú prítomné.

Príklad (`res/xml/answers/DEMO/DEMO_I.A_01_1234.example.xml`):

```xml
<?xml version='1.1' encoding='UTF-8'?>
<odpovede xml:lang="sk" predmet="DEMO" trieda="I.A" skupina="" kapitola="01" fileid="1234">
   <test id="demo01xnovaka" dat="2025-01-08T09:30:00">
      <otazka id="otq00001">a</otazka>
      <otazka id="otq00002">a</otazka>
   </test>
</odpovede>
```

---

## 8. Import odpovedí z fotiek/PDF cez AI

Pre papierové (ceruzka na papieri) písomky slúži stránka `GET
/admin/ai/importanswers` (ikona QR kódu v `/admin`).

### 8.1 Automatický import (`POST /admin/ai/importanswers`)

Učiteľ nahrá jednu alebo viac fotiek/skenov/PDF (pole `obrazky`, viacnásobný výber).
Pre každý súbor appka:
1. Skúsi najprv prečítať **QR kód** priamo (bez AI, cez `zxingcpp`) — QR kód s kľúčom
   testu sa tlačí na testy (pozri kapitolu 12). Ak sa nenájde, ako záložné riešenie
   pošle obrázok nakonfigurovanému AI providerovi (Claude/Gemini/Ollama), aby
   identifikoval ID testu z textového kódu v rohu.
2. Pre každé nájdené ID testu načíta zodpovedajúce zadanie z databázy (kontext pre AI).
3. Pošle obrázok + kontext zadania AI providerovi, ktorý extrahuje jednotlivé
   odpovede a prípadné nejasnosti.
4. Zapíše odpovede do príslušného súboru odpovedí (rovnaký formát ako
   `saveanswers`), pod danou `test_id`.

Výsledok (JSON, zobrazí sa v UI) obsahuje za každý súbor/test: počet zapísaných
odpovedí, prípadné chyby (zadanie nenájdené, chyba rozpoznávania) a zoznam nejasností,
ktoré AI pri čítaní odpovedí označilo.

AI provider sa vyberá v `.env` premennou `AI_PROVIDER` (`claude` | `gemini` |
`ollama`) — Ollama nepodporuje PDF, len obrázky.

### 8.2 Ručný import jedného testu (`POST /admin/ai/importmanual/{kluc}`)

Pre prípad, že AI import zlyhá alebo učiteľ chce odpovede zadať ručne — rovnaký
formát formulárových dát ako `saveanswers`, len bez kontroly časového okna testu.

---

## 9. AI nápoveda pre žiakov (`/ai/napoveda`)

Kým žiak píše test, môže si pri každej otázke kliknúť na tlačidlo nápovedy (`<span
class="ai-napoveda-btn">`). To zavolá `GET /ai/napoveda?otazka_id=...&test_id=...` —
appka:

1. Nájde otázku v aktuálnom teste žiaka a zostaví kontext: text otázky, možnosti (pri
   MCQ), existujúce ručne napísané `<napoveda>` v databáze otázok (celoplošné vždy,
   plus všetky kľúčované podľa toho, ktorú možnosť žiak práve zvolil, ak je väzba
   cez `pre`/`napoveda_key` — jedna odpoveď môže mať aj viac priradených nápovedí),
   vzorovú odpoveď (`<vzor>`) a kľúčové slová.
2. Skontroluje limit: appka počíta **celkový počet už použitých nápovied v rámci
   celého testu** (naprieč všetkými otázkami) a porovná ho s počtom otázok v teste —
   ide teda o spoločný rozpočet ("počet otázok" nápovied na celý test), nie o strop
   na jednu otázku; žiak tak môže minúť viac nápovied na jednu otázku a menej na iné.
   Ak je rozpočet vyčerpaný, appka pošle `napoveda_limit` event namiesto textu
   nápovedy.
3. Zavolá lokálny Ollama model (`OLLAMA_MODEL`, predvolene `llama3.1`) so systémovým
   promptom (`aihelp_system.md.j2`) — AI má dať **presne jednu vetu** nápovedy bez
   priameho prezradenia správnej odpovede, vždy v angličtine, plus 3–5 kľúčových
   pojmov (`KEYS:`).
4. Odpoveď sa streamuje cez Server-Sent Events (`text/event-stream`) — žiak vidí text
   nápovedy postupne, ako ju model generuje.
5. Použitie sa zaznamená do `res/xml/feedback/{predmet}/...xml` (element `<zapis>`)
   — slúži na sledovanie histórie nápovied a spätnú väzbu.

### `POST /ai/feedback`

Žiak môže po prečítaní nápovedy označiť, či mu pomohla — appka zapíše `val="1"`
(pomohla) alebo `val="0"` (nepomohla) do príslušného `<zapis>` v súbore feedbacku.
Táto história (`helped`/`not_helped` kľúčové slová z predošlých pokusov) sa
následne používa ako kontext pre budúce nápovedy k tej istej otázke — appka sa učí,
ktoré typy nápovied fungujú.

### XSD štruktúra `feedback.xsd`

Koreňový element `<feedback>` — **povinné**: `fileid`. **Voliteľné**: `predmet`,
`trieda`, `skupina`, `kapitola`, `autor`.

Element `<zapis>` — **povinné**: `datum` (ISO dátum a čas), `otazka_id`, `test_id`,
`val` (`"1"`, `"0"` alebo `""` = zatiaľ neohodnotené). **Voliteľné**: `id` (hash
záznamu — jednoznačne identifikuje zápis, keď doň appka neskôr dopĺňa `<hint>`/
`<keys>` počas streamovania odpovede, a keď žiak dodatočne odošle hodnotenie cez
`/ai/feedback`), vnorené `<hint>` (text AI nápovedy zobrazenej žiakovi) a `<keys>`
(kľúčové slová z `KEYS:` riadku AI odpovede — používajú sa ako kontext pre budúce
nápovedy k tej istej otázke).

Príklad (`res/xml/feedback/DEMO/DEMO_I.A_01_1234.example.xml`):

```xml
<?xml version='1.0' encoding='UTF-8'?>
<feedback fileid="1234">
   <zapis id="a1b2c3d4e5f6a7b8" datum="2025-01-08T09:20:00" otazka_id="otq00003" test_id="demo01xnovaka" val="1">
      <hint>Think about what happens to the source code before it can be executed.</hint>
      <keys>interpreter, kompilátor, zdrojový kód</keys>
   </zapis>
</feedback>
```

---

## 10. Opravovanie a bodovanie

### 10.1 MCQ otázky — automatické bodovanie

Pri MCQ otázkach appka body počíta automaticky. Keď test skončí (`stav == 'after'`
pri `GET /{kluc}`), appka zavolá `store_mcq_scores`, ktoré porovná žiacku odpoveď so
správnou odpoveďou zo zadania a zapíše body priamo do súboru odpovedí. Žiak potom
uvidí výsledné skóre a prípadnú **známku** priamo na úvodnej stránke po zadaní kľúča
(mapovanie percenta na známku podľa `scale.xsl` — pozri nižšie).

### 10.2 Otvorené/praktické otázky — ručné hodnotenie

`GET /admin/showresult/{kluc}` zobrazí učiteľovi formulár na opravu jedného žiaka —
pre každú otvorenú otázku vidí jeho odpoveď (readonly textové pole), pole na zadanie
bodov (`<input type="number" min="0" max="{body}">`) a komentár. Pri MCQ otázkach
vidí navyše rýchle značky správne/nesprávne/neisté (✓ / ✗ / ?) na farebné odlíšenie.

Uloženie hodnotenia: `POST /admin/savemarks/{kluc}` — zapíše `body` (`param='body'`
pre otvorené otázky) alebo `koment` (komentár) do príslušného `<otazka>` elementu v
súbore odpovedí, naviazané na presný `dat` (dátum odovzdania), aby sa neprepísalo
neskoršie odovzdanie.

### 10.3 Škálovanie na známku (`scale.xsl`)

Percento získaných bodov sa prevádza na klasickú 5-stupňovú známku podľa hraníc
(v XSLT premenné `min1..min5`/`max1..max5`), predvolene:

| Známka | Rozsah percent |
|---|---|
| 1 (výborný) | 90–100 % |
| 2 (chválitebný) | 80–89 % |
| 3 (dobrý) | 70–79 % |
| 4 (dostatočný) | 60–69 % |
| 5 (nedostatočný) | 0–59 % |

Tieto hranice sú v súbore `res/xslt/scale.xsl` a platia globálne pre celú appku —
zmena si podľa `AGENTS.md` vyžaduje reštart servera (Saxon si kešuje skompilované
šablóny).

### 10.4 Štatistiky skupiny (`groupstatistics`)

`POST /admin/groupstatistics` (ikona grafu v prehľade `/admin`) zobrazí štatistiku
konkrétnej sady testov (predmet/trieda/skupina/kapitola/fileid): úspešnosť po
kategóriách a jednotlivých otázkach (percento, počet správnych/nesprávnych), spolu s
celkovým percentom skupiny.

---

## 11. AI hodnotenie otvorených odpovedí (`aievaluate`)

Namiesto ručného bodovania môže učiteľ na stránke výsledkov kliknúť na tlačidlo *AI
evaluation* (ikona robota, `#ai-evaluate-btn`), ktoré volá `POST
/admin/ai/evaluate-open`.

Priebeh:
1. Appka načíta všetky **otvorené** otázky testu daného žiaka (cez XQuery
   `openquestions.xq`) spolu s jeho odpoveďami, vzorovou odpoveďou (`<vzor>`) a
   kľúčovými slovami (`klucove_slova`).
2. Vo vzorovej odpovedi nahradí zástupné symboly (`{meno}`, `{priezvisko:low rep}`
   atď.) skutočnými údajmi žiaka (meno/priezvisko/trieda z tests XML), vrátane
   transformácií `low` (malé písmená), `upp` (veľké písmená), `rep` (odstránenie
   diakritiky).
3. Všetky otvorené otázky žiaka pošle naraz modelu Claude (`ANTHROPIC_MODEL`,
   predvolene `claude-sonnet-5`) so systémovým promptom
   (`app/templates/aievaluate_system.md`).
4. Vráti pre každú otázku návrh bodového hodnotenia a odôvodnenie (`{id, body,
   dovod}`) — učiteľ návrh vidí vo formulári a môže ho pred uložením upraviť.

Toto hodnotenie je len **návrh** — konečné uloženie bodov ide vždy cez `POST
/admin/savemarks/{kluc}` popísané v kapitole 10.2, teda učiteľ má vždy poslednú kontrolu.

Poznámka: AI hodnotenie otvorených otázok (`evaluate-open`) používa vždy Anthropic
Claude natvrdo (nie nastavenie `AI_PROVIDER` z `.env`, ktoré ovplyvňuje len import
odpovedí z fotiek) — over si v `.env`, že je nastavený platný `ANTHROPIC_API_KEY`, aj
keby bol `AI_PROVIDER=ollama` alebo `gemini` pre import.

---

## 12. Prehľady a report nápovedy (`feedbackreport`)

`POST /admin/feedbackreport` zobrazí prehľad všetkých AI nápovedí použitých v danej
sade testov — zoskupené po kategóriách, s pomerom koľkokrát nápoveda žiakovi pomohla
(`val="1"`) verzus nepomohla (`val="0"`) verzus nebola vôbec hodnotená. Slúži
učiteľovi na spätnú väzbu, ktoré otázky/nápovede reálne fungujú.

---

## 13. Export a tlač do PDF

Všetky exporty sú dostupné z riadku danej sady testov v prehľade `/admin` (ikony v
stĺpci "Akcie").

| Endpoint | Ikona v UI | Čo vygeneruje |
|---|---|---|
| `POST /admin/downloadtests` | tlačiareň | PDF so **zadaniami všetkých testov** danej sady, pripravené na tlač a rozdanie žiakom — každý test má vlastný QR kód s kľúčom v rohu (na neskorší automatický import fotiek, kapitola 8) |
| `POST /admin/downloadresults` | šípka nadol | PDF so **súhrnom výsledkov** celej sady (všetci žiaci) |
| `GET /admin/downloadresult/{kluc}` | — (z detailu jedného žiaka) | PDF s výsledkom **jedného konkrétneho žiaka** |
| `POST /admin/downloadcodes` | prázdny hárok | PDF len s **QR kódmi/kľúčmi** testov (bez zadania) — vhodné napr. na vytlačenie štítkov/lístočkov s kódmi zvlášť |

Generovanie PDF beží cez Apache FOP (XSL-FO transformácia, `res/xslt/downloadtests.xsl`,
`downloadresult.xsl`, `downloadcodes.xsl`) — appka volá `fop` ako externý proces, musí
byť dostupný v `PATH` na serveri.

---

## 14. Archivácia a údržba

Tieto skripty spúšťa učiteľ/admin ručne z príkazového riadka na serveri, nie z appky.

- **`scripts/archive_predmet.sh <predmet>`** — zabalí `tests/`, `answers/` aj
  `feedback/` adresáre daného predmetu do `.tar.xz` archívu v
  `res/xml/archiv/<školský_rok>/` (školský rok sa počíta od septembra). S prepínačom
  `-d` po zabalení aj vymaže pôvodné súbory. Príklad: `bash scripts/archive_predmet.sh -d SXT4`.
- **`scripts/cleanup_answers.py`** — jednorazový údržbový skript: v každom súbore
  odpovedí ponechá len posledný (najnovší) pokus na žiaka, staršie duplicitné
  záznamy vymaže.
- **`scripts/migrate_add_headers.py`**, **`scripts/migrate_ids.py`**,
  **`scripts/migrate_feedback.ids.py`** — jednorazové migračné skripty použité pri
  minulých zmenách dátového formátu (napr. prechod na hashované `id` otázok). Bežný
  učiteľ ich za normálnych okolností nepotrebuje spúšťať — slúžia len ako referencia,
  ak by bolo potrebné migrovať staré dáta znova.

---

## 15. Prehľadová tabuľka všetkých endpointov

| Cesta | Metóda | Na čo slúži |
|---|---|---|
| `/` | GET | Úvodná stránka — zadanie kľúča testu žiakom |
| `/{kluc}` | GET | Zobrazenie/vyplnenie testu žiakom (podľa stavu: pred/počas/po; `?edit=true` = editovateľný formulár) |
| `/admin` | GET | Prehľad všetkých testov prihláseného učiteľa |
| `/admin/{kluc}` | GET | Zobrazenie/úprava konkrétneho testu v administrátorskom režime |
| `/admin/selectcreate` | GET | Formulár na vytvorenie novej sady testov |
| `/admin/createtests` | POST | Vygeneruje novú sadu testov pre triedu/skupinu |
| `/admin/regeneratetests` | POST | Prežrebuje existujúcu (ešte neodovzdanú) sadu testov |
| `/admin/deletetests` | DELETE | Vymaže sadu testov (voliteľne aj odpovede/feedback) |
| `/saveanswers/{kluc}` | POST | Žiak odošle svoje odpovede (aj súbory) |
| `/stoptime/{kluc}` | POST | Zaznamená čas ukončenia písania konkrétneho žiaka |
| `/admin/setpaused` | POST | Pozastaví/obnoví kategóriu alebo otázku |
| `/admin/changetime` | POST | Zmení začiatok/koniec písania (pre celú sadu alebo jedného žiaka) |
| `/admin/showresult/{kluc}` | GET | Formulár na opravu/hodnotenie jedného žiaka |
| `/admin/savemarks/{kluc}` | POST | Uloží body a komentáre k odpovediam žiaka |
| `/admin/groupstatistics` | POST | Štatistika úspešnosti skupiny/kategórií/otázok |
| `/admin/downloadresult/{kluc}` | GET | PDF s výsledkom jedného žiaka |
| `/admin/downloadtests` | POST | PDF so zadaniami všetkých testov sady (s QR kódmi) |
| `/admin/downloadresults` | POST | PDF so súhrnom výsledkov celej sady |
| `/admin/downloadcodes` | POST | PDF len s QR kódmi/kľúčmi testov |
| `/admin/selectquestions` | GET | Formulár na výber predmetu pre editor otázok |
| `/admin/showquestions` | POST | Zobrazí databázu otázok predmetu (editor + štatistika) |
| `/admin/process_chapter` | POST | Vytvorí/premenuje/vymaže kapitolu |
| `/admin/process_category` | POST | Vytvorí/upraví/vymaže/obnoví kategóriu |
| `/admin/process_question` | POST | Vytvorí/upraví/vymaže/obnoví otázku |
| `/admin/question` | GET | Surové dáta otázky pre editačný formulár |
| `/admin/category` | GET | Surové dáta kategórie pre editačný formulár |
| `/admin/is_used` | GET | Zistí, či je kategória/otázka použitá v teste |
| `/ai/napoveda` | GET | AI nápoveda pre žiaka (SSE stream, Ollama) |
| `/ai/feedback` | POST | Žiak ohodnotí, či mu AI nápoveda pomohla |
| `/admin/feedbackreport` | POST | Prehľad úspešnosti AI nápovedí danej sady |
| `/admin/ai/importanswers` (GET) | GET | Stránka na nahratie fotiek/skenov odpovedí |
| `/admin/ai/importanswers` (POST) | POST | Hromadný AI import odpovedí z fotiek/PDF |
| `/admin/ai/importmanual/{kluc}` | POST | Ručný zápis odpovedí jedného žiaka (bez AI) |
| `/admin/ai/evaluate-open` | POST | AI návrh hodnotenia otvorených odpovedí žiaka (Claude) |
| `/pubres/*` | GET | Statické súbory (CSS, JS, obrázky) |

---

## 16. Neisté/neoverené body

- Presný algoritmus anti-odpisovacieho generovania (`sedenie`) v `createtests.xsl` je
  pomerne zložitý (tunelované parametre, `generate-id()` korelácia) — v tejto
  príručke je opísaný len z pohľadu výsledného správania (žiadny zdieľaný výber s
  priamymi susedmi), nie implementačný detail.
- Presný vzorec anti-cheating rozhodovania (čo presne znamená "priamy sused" pri
  nepravidelných radoch/nekompletných sedeniach) som neoveroval do hĺbky XSLT kódu —
  v texte je opísaný len na základe poznámky v `AGENTS.md` a signatúr funkcií v
  `createtests.xsl`.
