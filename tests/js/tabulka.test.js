//Testy cistych funkcii z pubres/js/tabulka.js (vkladanie tabulky zo schranky do editora otazok); spustenie: node --test tests/js/
//Subor je klasicky skript pre prehliadac (bez exportov), preto sa nacita cez vm a funkcie sa citaju z globalneho objektu kontextu.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../pubres/js/tabulka.js'), 'utf8'), ctx);
const {parsujCsv, parsujMarkdown, parsujSchranku, escapujXml, zostavXmlTabulky,
   novyStavTabulky, stavZRiadkov, pridajRiadokTabulky, pridajStlpecTabulky, odstranRiadokTabulky, odstranStlpecTabulky,
   prepniBunkuTabulky, prepniStlpecTabulky, nastavHlavickuTabulky, povoleneZVystupu, stavJePrazdny, xmlTabulky} = ctx;

//pole z vm kontextu ma iny prototyp Array, deepStrictEqual by ho odmietol
const rovne = (skutocne, ocakavane) => assert.deepEqual(JSON.parse(JSON.stringify(skutocne)), ocakavane);

test('TSV z tabulkoveho procesora, koncovy novy riadok nepridava prazdny riadok', () => {
   rovne(parsujSchranku('A\tB\tY\n0\t0\t0\n0\t1\t1\n'), [['A', 'B', 'Y'], ['0', '0', '0'], ['0', '1', '1']]);
});

test('posledny riadok bez noveho riadku sa nacita', () => {
   rovne(parsujSchranku('a\tb\n1\t2'), [['a', 'b'], ['1', '2']]);
});

test('CRLF konce riadkov', () => {
   rovne(parsujSchranku('a\tb\r\n1\t2\r\n'), [['a', 'b'], ['1', '2']]);
});

test('prazdny vstup da prazdne pole', () => {
   rovne(parsujSchranku(''), []);
});

test('bunky sa orezavaju a kratsie riadky sa dopln prazdnymi na rovnaku sirku', () => {
   rovne(parsujSchranku(' a \t b \t c\n1\n'), [['a', 'b', 'c'], ['1', '', '']]);
});

test('CSV so bodkociarkou, desatinna ciarka ostane v bunke', () => {
   rovne(parsujSchranku('A;B;Y\n0;0;0\n1;1;1,5'), [['A', 'B', 'Y'], ['0', '0', '0'], ['1', '1', '1,5']]);
});

test('CSV s ciarkou a uvodzovkami: "1,5", zdvojena uvodzovka', () => {
   rovne(parsujSchranku('A,B,Y\n"1,5",1,"x ""q"""'), [['A', 'B', 'Y'], ['1,5', '1', 'x "q"']]);
});

test('v uvodzovkach moze byt aj novy riadok a tabulator', () => {
   rovne(parsujSchranku('a\t"b\nc\td"\te'), [['a', 'b\nc\td', 'e']]);
});

test('uvodzovka v strede bunky je obycajny znak', () => {
   rovne(parsujSchranku('5" displej;x'), [['5" displej', 'x']]);
});

test('Markdown: oddelovaci riadok --- sa vynecha, aj so zarovnanim', () => {
   rovne(parsujSchranku('| a | b |\n|---|:--:|\n| 1 | 2 |'), [['a', 'b'], ['1', '2']]);
});

test('Markdown bez okrajovych zvislikov a s escapovanym \\|', () => {
   rovne(parsujSchranku('a | b\n--- | ---\nx\\|y | 2'), [['a', 'b'], ['x|y', '2']]);
});

test('Markdown s odsadenim a medzerami na konci riadkov', () => {
   rovne(parsujSchranku('  | a | b |  \n  |---|---|  \n  | 1 | 2 |   '), [['a', 'b'], ['1', '2']]);
});

test('automaticka detekcia: tabulator ma prednost pred ostatnymi', () => {
   rovne(parsujSchranku('a;b\tc|d,e'), [['a;b', 'c|d,e']]);
});

test('automaticka detekcia: | pred ; a ,', () => {
   rovne(parsujSchranku('a;b | c,d'), [['a;b', 'c,d']]);
});

test('automaticka detekcia: ; pred ,', () => {
   rovne(parsujSchranku('1,5;2,5'), [['1,5', '2,5']]);
});

test('bez oddelovaca je jeden stlpec', () => {
   rovne(parsujSchranku('a\nb'), [['a'], ['b']]);
});

test('vynuteny oddelovac prebije automatiku', () => {
   rovne(parsujSchranku('A;B,C\n1;2,3', ','), [['A;B', 'C'], ['1;2', '3']]);
   rovne(parsujSchranku('A;B,C\n1;2,3', ';'), [['A', 'B,C'], ['1', '2,3']]);
   rovne(parsujSchranku('A\tB\n1\t2', '\t'), [['A', 'B'], ['1', '2']]);
});

test('parsujCsv a parsujMarkdown sa daju volat samostatne', () => {
   rovne(parsujCsv('a;b\n', ';'), [['a', 'b']]);
   rovne(parsujMarkdown('|a|b|\n|-|-|\n|1|2|'), [['a', 'b'], ['1', '2']]);
});

test('escapujXml escapuje & < > a uvodzovky', () => {
   assert.equal(escapujXml('a&b<c>"d"'), 'a&amp;b&lt;c&gt;&quot;d&quot;');
   assert.equal(escapujXml("plain 'x'"), "plain 'x'");
});

const TABULKA = [['A', 'B', 'Y'], ['0', '1', '1'], ['1', '0', '1']];

test('XML tabulky s hlavickou a stlpcom ako polami na vyplnenie (3 medzery odsadenie)', () => {
   const vystup = new Set(['1,2', '2,2']);
   assert.equal(zostavXmlTabulky(TABULKA, true, vystup, '01'), [
      '<tabulka povolene="01">',
      '   <hlavicka>',
      '      <bunka>A</bunka>',
      '      <bunka>B</bunka>',
      '      <bunka>Y</bunka>',
      '   </hlavicka>',
      '   <riadok>',
      '      <bunka>0</bunka>',
      '      <bunka>1</bunka>',
      '      <bunka odpoved="1"/>',
      '   </riadok>',
      '   <riadok>',
      '      <bunka>1</bunka>',
      '      <bunka>0</bunka>',
      '      <bunka odpoved="1"/>',
      '   </riadok>',
      '</tabulka>',
   ].join('\n'));
});

test('bez hlavicky su vsetky riadky <riadok>', () => {
   const xml = zostavXmlTabulky(TABULKA, false, new Set(['0,0']), '');
   assert.ok(!xml.includes('<hlavicka>'));
   assert.equal(xml.split('<riadok>').length - 1, 3);
   assert.ok(xml.includes('<bunka odpoved="A"/>'));
});

test('bunky sa jednotlive oznacuju podla riadok,stlpec', () => {
   const xml = zostavXmlTabulky(TABULKA, true, new Set(['1,0']), '');
   assert.equal(xml.split('odpoved=').length - 1, 1);
   assert.ok(xml.includes('<bunka odpoved="0"/>'));
});

test('hodnoty aj povolene znaky sa escapuju v XML', () => {
   const xml = zostavXmlTabulky([['a<b', '"q"'], ['&', 'x']], false, new Set(['1,0']), '"&');
   assert.ok(xml.startsWith('<tabulka povolene="&quot;&amp;">'));
   assert.ok(xml.includes('<bunka>a&lt;b</bunka>'));
   assert.ok(xml.includes('<bunka>&quot;q&quot;</bunka>'));
   assert.ok(xml.includes('<bunka odpoved="&amp;"/>'));
});


//--- stav editora tabulky ---

const kluce = (stav) => [...stav.vystup].sort();

//hlavicka + 2 riadky tela, 3 stlpce: a b c / 1 2 3 / 4 5 6
function vzorovyStav(maHlavicku = true) {
   return {riadky: [['a', 'b', 'c'], ['1', '2', '3'], ['4', '5', '6']], vystup: new Set(), maHlavicku, povolene: ''};
}

test('predvolena tabulka: hlavicka a dva riadky tela, tri stlpce, prazdna', () => {
   const stav = novyStavTabulky();
   assert.equal(stav.riadky.length, 3);
   assert.ok(stav.riadky.every(r => r.length === 3 && r.every(t => t === '')));
   assert.equal(stav.maHlavicku, true);
   assert.equal(stav.vystup.size, 0);
   assert.ok(stavJePrazdny(stav));
});

test('stavJePrazdny: text alebo pole znamena, ze tabulka nie je prazdna', () => {
   const stav = novyStavTabulky();
   stav.riadky[1][1] = ' x ';
   assert.ok(!stavJePrazdny(stav));
   const stav2 = novyStavTabulky();
   stav2.vystup.add('1,1');
   assert.ok(!stavJePrazdny(stav2));
});

test('pridanie riadku a stlpca doplni prazdne bunky v kazdom riadku', () => {
   const stav = vzorovyStav();
   pridajRiadokTabulky(stav);
   pridajStlpecTabulky(stav);
   rovne(stav.riadky, [['a', 'b', 'c', ''], ['1', '2', '3', ''], ['4', '5', '6', ''], ['', '', '', '']]);
});

test('odstranenie riadku posunie oznacene polia pod nim a zahodi polia v nom', () => {
   const stav = vzorovyStav();
   pridajRiadokTabulky(stav);               //riadky 0..3
   ['1,0', '2,1', '3,2'].forEach(k => stav.vystup.add(k));
   assert.equal(odstranRiadokTabulky(stav, 2), true);
   rovne(stav.riadky, [['a', 'b', 'c'], ['1', '2', '3'], ['', '', '']]);
   assert.deepEqual(kluce(stav), ['1,0', '2,2']);
});

test('hlavicka sa odstranit neda a musi ostat aspon jeden riadok tela', () => {
   const stav = vzorovyStav();
   assert.equal(odstranRiadokTabulky(stav, 0), false);
   assert.equal(odstranRiadokTabulky(stav, 2), true);
   assert.equal(odstranRiadokTabulky(stav, 1), false);
   assert.equal(stav.riadky.length, 2);
});

test('bez hlavicky sa da odstranit aj prvy riadok, ale ostane aspon jeden', () => {
   const stav = vzorovyStav(false);
   assert.equal(odstranRiadokTabulky(stav, 0), true);
   assert.equal(odstranRiadokTabulky(stav, 0), true);
   assert.equal(odstranRiadokTabulky(stav, 0), false);
   rovne(stav.riadky, [['4', '5', '6']]);
});

test('odstranenie stlpca posunie oznacene polia vpravo od neho', () => {
   const stav = vzorovyStav();
   ['1,0', '1,1', '2,2'].forEach(k => stav.vystup.add(k));
   assert.equal(odstranStlpecTabulky(stav, 1), true);
   rovne(stav.riadky, [['a', 'c'], ['1', '3'], ['4', '6']]);
   assert.deepEqual(kluce(stav), ['1,0', '2,1']);
});

test('posledny stlpec sa odstranit neda', () => {
   const stav = {riadky: [['a'], ['1']], vystup: new Set(), maHlavicku: true, povolene: ''};
   assert.equal(odstranStlpecTabulky(stav, 0), false);
   assert.equal(stav.riadky[0].length, 1);
});

test('prepnutie bunky: tam a spat, hlavicka sa prepnut neda', () => {
   const stav = vzorovyStav();
   assert.equal(prepniBunkuTabulky(stav, 1, 1), true);
   assert.deepEqual(kluce(stav), ['1,1']);
   assert.equal(prepniBunkuTabulky(stav, 1, 1), true);
   assert.deepEqual(kluce(stav), []);
   assert.equal(prepniBunkuTabulky(stav, 0, 1), false);
   assert.deepEqual(kluce(stav), []);
});

test('prepnutie stlpca: najprv oznaci vsetky bunky tela, potom ich zrusi; hlavicku preskoci', () => {
   const stav = vzorovyStav();
   prepniStlpecTabulky(stav, 2);
   assert.deepEqual(kluce(stav), ['1,2', '2,2']);
   prepniStlpecTabulky(stav, 2);
   assert.deepEqual(kluce(stav), []);
});

test('prepnutie stlpca, v ktorom je oznacena len cast, ho oznaci cely', () => {
   const stav = vzorovyStav();
   stav.vystup.add('1,2');
   prepniStlpecTabulky(stav, 2);
   assert.deepEqual(kluce(stav), ['1,2', '2,2']);
});

test('bez hlavicky sa prepnutim stlpca oznaci aj prvy riadok', () => {
   const stav = vzorovyStav(false);
   prepniStlpecTabulky(stav, 0);
   assert.deepEqual(kluce(stav), ['0,0', '1,0', '2,0']);
});

test('zapnutie hlavicky zrusi polia v prvom riadku', () => {
   const stav = vzorovyStav(false);
   ['0,0', '0,1', '1,1'].forEach(k => stav.vystup.add(k));
   nastavHlavickuTabulky(stav, true);
   assert.equal(stav.maHlavicku, true);
   assert.deepEqual(kluce(stav), ['1,1']);
});

test('zapnutie hlavicky pri jedinom riadku prida riadok tela', () => {
   const stav = {riadky: [['a', 'b']], vystup: new Set(), maHlavicku: false, povolene: ''};
   nastavHlavickuTabulky(stav, true);
   rovne(stav.riadky, [['a', 'b'], ['', '']]);
});

test('povolene znaky z poli: kazdy znak raz, v poradi vyskytu', () => {
   const stav = {riadky: [['x', 'y'], ['10', '01'], ['a', 'b']], vystup: new Set(['1,0', '1,1']), maHlavicku: true, povolene: ''};
   assert.equal(povoleneZVystupu(stav), '10');
   stav.vystup.add('2,0');
   assert.equal(povoleneZVystupu(stav), '10a');
   assert.equal(povoleneZVystupu({riadky: [['a']], vystup: new Set(), maHlavicku: false, povolene: ''}), '');
});

test('stavZRiadkov: kopia, bez poli; po hlavicke vzdy aspon jeden riadok tela', () => {
   const vstup = [['a', 'b']];
   const stav = stavZRiadkov(vstup, true);
   rovne(stav.riadky, [['a', 'b'], ['', '']]);
   assert.deepEqual(vstup, [['a', 'b']]);       //vstup sa nezmenil
   assert.equal(stav.vystup.size, 0);
   assert.equal(stav.povolene, '');
   rovne(stavZRiadkov([['a', 'b']], false).riadky, [['a', 'b']]);
});

test('stavZRiadkov z prazdneho vstupu da predvolenu tabulku', () => {
   assert.equal(stavZRiadkov([], true).riadky.length, 3);
});

test('xmlTabulky zostavi XML zo stavu vratane poli a povolenych znakov', () => {
   const stav = {riadky: [['A', 'Y'], ['0', '1']], vystup: new Set(['1,1']), maHlavicku: true, povolene: '01'};
   assert.equal(xmlTabulky(stav), [
      '<tabulka povolene="01">',
      '   <hlavicka>',
      '      <bunka>A</bunka>',
      '      <bunka>Y</bunka>',
      '   </hlavicka>',
      '   <riadok>',
      '      <bunka>0</bunka>',
      '      <bunka odpoved="1"/>',
      '   </riadok>',
      '</tabulka>',
   ].join('\n'));
});
