import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outDir = "C:/Users/Anvar/Desktop/cat/outputs/tuatara_grouped";
await fs.mkdir(outDir, { recursive: true });
const wb = Workbook.create();
const instructions = wb.worksheets.add("Instructions");
const test = wb.worksheets.add("Test");
const sections = wb.worksheets.add("Sections");
const groups = wb.worksheets.add("Groups");
const questions = wb.worksheets.add("Questions");

const passage = `The tuatara – past and future

The New Zealand species of lizard, the tuatara, is firmly embedded in the national psyche: an icon for today which dates from the age of dinosaurs; an ancient reptile common before the arrival of humans.

When European explorers reached New Zealand in 1769 they found two large islands, which together they called the “mainland”, and many tiny offshore islands around the coast. The naturalists who came with the explorers disregarded the tuatara, though it is now several times more numerous than it once was on the mainland. One of the first scientists who realised that aspects of tuatara anatomy were odd – unchanged for tens of thousands of years – was Albert Gunther in 1876. Gunther believed the tuatara was one of the most valuable objects in zoological anatomical collections, and also noted, in passing, that the reptile was likely to become extinct. From the perspective of the tuatara, it is striking how Gunther’s contentions were products of their age, strongly influenced by Charles Darwin’s theory, which had only recently been published. Their views were something like this: “Extinction is a natural process. It is sad that species disappear, but that is part of nature.”

There is a second important aspect of Gunther’s work. He recorded, correctly, that some of the mammals introduced by Europeans were predators of the tuatara – particularly rats. But what he did not realise was that New Zealand has two species of rat, both introduced, both with an appetite for tuatara: the ship’s rat came with European explorers and settlers; the kiore rat had already been brought by Polynesian explorers from Pacific islands. Gunther failed to recognise the distinction, believing all rats to be a relatively recent introduction.

Little further research was conducted until Ian Crook of the NZ Wildlife Service published his findings in 1973, which can be summarised as follows. Tuatara thrive on offshore islands with no rats. Tuatara never survived on islands with ship’s rats. On a few islands, however, there was declining evidence that tuatara and kiore could coexist. Rather, Crook proposed, kiore probably only arrived recently on such islands, and thus the small populations represent extinctions in progress.

Throughout the 1990s, Richard Holdaway and his colleagues at Victoria University in Wellington documented the surprising discovery that kiore probably arrived about 800 years ago. How did this happen? Presumably, Holdaway argued, the kiore were brought by Polynesian explorers who visited the country but did not settle. Thereafter, the rats were agents of ecological warfare, exterminating perhaps 1,000–3,000 species. Thus, tuatara and many other species were already rare or extinct when permanent human inhabitants – the Maori – arrived around 1300. This hypothesis is still being debated, but the evidence continues to accumulate in its favour.

Conservation practice has changed dramatically since Crook’s findings were published in 1973. Eradication of rats from any given environment was believed to be virtually impossible until about 1980, but since then has become routine. Enormous conservation benefits are accruing as newly rat-free offshore islands are providing sanctuaries for the country’s rarest species. In 1995, for example, Nicola Nelson’s Department of Conservation established 68 tuatara on Titi Island. Four more populations of tuatara have been established elsewhere under similar conditions.

Today, numbers of tuatara are still a fraction of what they once were, but for the first time in 800 years the decline has been reversed.

While the recovery of rare species is itself a good thing, the truly significant outcome of this research is that it liberates the imagination. If we can remove predatory introduced mammals from islands, why not from the mainland? Our rivers, for example, are full of surrogate rats, in the form of introduced species of fish called trout. Should we now go further and consider reintroducing native fish to our mainland rivers? Similarly, can bellbirds and tuis replace birds like starlings and mynas?

The answers to such questions are uncertain, and opposing sides will doubtless be fiercely debated. But the role of scientific knowledge in illuminating the past will be crucial. Perhaps our children will come to believe in the restoration of species, in the same way that our generation refuses to accept the extinction of species. Creating the future we wish for our children and ourselves is not primarily about the past, but about imagining and then using the past. For 80 million years until humans arrived, tuatara occurred throughout New Zealand – might they do so again?`;

instructions.getRange("A1:B7").values = [
  ["IELTS Mock — Ready-to-import workbook", ""],
  ["Purpose", "Academic Reading Passage 3, Questions 27–40"],
  ["Upload", "Admin → Import Excel tests → choose this file → review → confirm"],
  ["Grouped layout", "Questions 36–40 use summary_36_40 and render as one inline worksheet."],
  ["Ordinary layout", "Questions 27–35 remain standard multiple-choice cards."],
  ["Compatibility", "Do not rename worksheets or change row-1 headers."],
  ["Review", "Verify the cleaned passage and answer key before publishing."],
];

test.getRange("A1:B4").values = [["field","value"],["title","The tuatara – past and future"],["description","Academic Reading Passage 3 with Questions 27–40."],["category","reading"]];
sections.getRange("A1:D2").values = [["section_order","section_type","time_limit_minutes","passage_text"],[1,"reading",20,passage]];

const layout = `<h3>What conclusions can we draw?</h3><p>The most important result of the tuatara research is that it frees our [[36]].</p><p>For example, there are many similarities between rats and [[37]]. Should we now go further and consider reintroducing [[38]] to our mainland rivers?</p><p>Perhaps our children will come to believe in the [[39]] of species, in the same way that our generation refuses to accept [[40]] of species.</p><div><p><strong>A</strong> natural evolution</p><p><strong>B</strong> creative thought</p><p><strong>C</strong> indigenous plants</p><p><strong>D</strong> trout</p><p><strong>E</strong> pollution</p><p><strong>F</strong> restoration</p><p><strong>G</strong> native fish</p><p><strong>H</strong> extinction</p></div>`;
groups.getRange("A1:G2").values = [["section_order","group_key","group_order","layout_type","title","instructions","layout_html"],[1,"summary_36_40",36,"notes","What conclusions can we draw?","<p>Questions 36–40</p><p>Complete the summary using the list of words, <strong>A–H</strong>, below.</p><p>Write the correct letter, <strong>A–H</strong>, in boxes 36–40.</p>",layout]];

const mcq = (order,prompt,options,answer,reference) => [1,order,"mcq",prompt,options.join(" | "),answer,"",reference,"",""];
const gap = (order,prompt,answer,reference) => [1,order,"gap",prompt,"",answer,"",reference,"","summary_36_40"];
const qrows = [
  ["section_order","question_order","question_type","prompt","options","correct_answer","explanation","passage_reference","notes_for_admin","group_key"],
  mcq(27,"What are we told about the Europeans who arrived in 1769?",["A They thought there was only one large island.","B They had not come to study natural history.","C They had no interest in the tuatara.","D They sent a tuatara to the British Museum."],"C They had no interest in the tuatara.","The naturalists who came with the explorers disregarded the tuatara."),
  mcq(28,"What does the text say about Albert Gunther in paragraph 3?",["A He believed the tuatara could fetch a high price.","B He was typical of his generation of scientists.","C He disagreed with Charles Darwin's theory.","D He wanted to stop the tuatara becoming extinct."],"B He was typical of his generation of scientists.","Gunther’s contentions were products of their age, strongly influenced by Charles Darwin’s theory."),
  mcq(29,"What did Albert Gunther think about the rats in New Zealand?",["A They did not eat the tuatara.","B There was only one species of rat.","C There had always been rats in New Zealand.","D They were killed by Polynesians."],"B There was only one species of rat.","Gunther failed to recognise the distinction, believing all rats to be a relatively recent introduction."),
  mcq(30,"What did Ian Crook conclude from his research?",["A Tuatara are safe on small islands.","B Kiore rats kill more tuatara than ship’s rats.","C Ship’s rats kill more tuatara than kiore rats.","D Rats and tuatara cannot live together."],"D Rats and tuatara cannot live together.","Crook proposed that the small populations represent extinctions in progress."),
  mcq(31,"What were the findings of Richard Holdaway's research?",["A Maori settled more recently than previously thought.","B The first Polynesian explorers formed permanent settlements.","C Ship's rats are the oldest rat species in the country.","D Rats caused extinctions before any humans settled."],"D Rats caused extinctions before any humans settled.","Tuatara and many other species were already rare or extinct when permanent human inhabitants arrived around 1300."),
  mcq(32,"The available research supports Holdaway's theory but it has not been proved.",["YES","NO","NOT GIVEN"],"YES","This hypothesis is still being debated, but the evidence continues to accumulate in its favour."),
  mcq(33,"Nowadays, it is possible to totally destroy a population of rats on a small island.",["YES","NO","NOT GIVEN"],"YES","Eradication of rats ... has become routine."),
  mcq(34,"Crook was the first person to recognize the potential of offshore islands as sanctuaries.",["YES","NO","NOT GIVEN"],"NOT GIVEN","The passage does not state that Crook was the first person to recognise this potential."),
  mcq(35,"Tuatara numbers are continuing to fall.",["YES","NO","NOT GIVEN"],"NO","For the first time in 800 years the decline has been reversed."),
  gap(36,"The most important result of the tuatara research is that it frees our _____.","B","The truly significant outcome of this research is that it liberates the imagination."),
  gap(37,"There are many similarities between rats and _____.","D","Our rivers ... are full of surrogate rats, in the form of introduced species of fish called trout."),
  gap(38,"Consider reintroducing _____ to our mainland rivers.","G","Should we now go further and consider reintroducing native fish to our mainland rivers?"),
  gap(39,"Our children may come to believe in the _____ of species.","F","Perhaps our children will come to believe in the restoration of species."),
  gap(40,"Our generation refuses to accept _____ of species.","H","Our generation refuses to accept the extinction of species."),
];
questions.getRange(`A1:J${qrows.length}`).values = qrows;

for (const sheet of [instructions,test,sections,groups,questions]) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const used = sheet.getUsedRange();
  used.format.wrapText = true;
  used.format.verticalAlignment = "top";
  const header = sheet.getRangeByIndexes(0,0,1,used.columnCount);
  header.format = {fill:"#10213E",font:{bold:true,color:"#FFFFFF"},verticalAlignment:"center",wrapText:true};
  header.format.rowHeight = 28;
}
instructions.getRange("A1:B1").format.fill = "#1463E9";
instructions.getRange("A1:B1").format.font = {bold:true,color:"#FFFFFF",size:14};
instructions.getRange("A1:B7").format.borders = {preset:"insideHorizontal",style:"thin",color:"#DCE5EF"};

const widths = {
  Instructions:[18,82], Test:[22,76], Sections:[16,18,22,110], Groups:[16,20,16,17,35,72,115], Questions:[15,15,18,58,70,34,38,72,26,22]
};
for (const [name,vals] of Object.entries(widths)) vals.forEach((w,i)=>wb.worksheets.getItem(name).getRangeByIndexes(0,i,wb.worksheets.getItem(name).getUsedRange().rowCount,1).format.columnWidth=w);
sections.getRange("A2:D2").format.rowHeight = 190;
groups.getRange("A2:G2").format.rowHeight = 150;
questions.getRange(`A2:J${qrows.length}`).format.rowHeight = 66;
test.getRange("B4").dataValidation = {rule:{type:"list",values:["reading","listening","writing","speaking","full"]}};
sections.getRange("B2").dataValidation = {rule:{type:"list",values:["reading","listening","writing","speaking"]}};
groups.getRange("D2").dataValidation = {rule:{type:"list",values:["notes","table","flow"]}};
questions.getRange(`C2:C${qrows.length}`).dataValidation = {rule:{type:"list",values:["mcq","gap","matching","essay","speaking"]}};

for (const name of ["Instructions","Test","Sections","Groups","Questions"]) {
  const preview = await wb.render({sheetName:name,autoCrop:"all",scale:1,format:"png"});
  await fs.writeFile(`${outDir}/${name}.png`,new Uint8Array(await preview.arrayBuffer()));
}
console.log((await wb.inspect({kind:"table",range:"Questions!A1:J15",include:"values,formulas",tableMaxRows:15,tableMaxCols:10,maxChars:8000})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"formula error scan"})).ndjson);
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(`${outDir}/Tuatara_Passage_3_Grouped_Import.xlsx`);
