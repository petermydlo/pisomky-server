//Testy cistych funkcii z pubres/js/tabulka.js (vkladanie tabulky zo schranky do editora otazok); spustenie: node --test tests/js/
//Subor je klasicky skript pre prehliadac (bez exportov), preto sa nacita cez vm a funkcie sa citaju z globalneho objektu kontextu.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../pubres/js/tabulka.js'), 'utf8'), ctx);
const {parsujCsv, parsujMarkdown, parsujSchranku, escapujXml, zostavXmlTabulky} = ctx;

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
