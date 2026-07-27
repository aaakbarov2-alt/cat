(function(){
  "use strict";
  const root=document.getElementById("reader-review");
  if(!root)return;
  const reviews=[...root.querySelectorAll(".reader-question-review")];
  const passages=[...root.querySelectorAll(".reader-passage")];
  const nav=[...root.querySelectorAll("[data-review-target]")];
  const previous=document.getElementById("reader-previous");
  const next=document.getElementById("reader-next");
  const evidenceStatus=document.getElementById("reader-evidence-status");
  let current=0;

  function setEvidenceStatus(message){if(evidenceStatus)evidenceStatus.textContent=message}

  function normalizedWithMap(text){
    const chars=[],map=[];let lastSpace=false;
    const replacements={"’":"'","‘":"'","“":"\"","”":"\"","–":"-","—":"-","\u00a0":" "};
    for(let i=0;i<text.length;i++){
      let char=(replacements[text[i]]||text[i]).toLowerCase();
      if(/\s/.test(char)){if(lastSpace)continue;char=" ";lastSpace=true}else lastSpace=false;
      chars.push(char);map.push(i);
    }
    return {text:chars.join(""),map};
  }
  function normalize(text){return normalizedWithMap(text||"").text.replace(/[^a-z0-9%€£$,'" -]/g," ").replace(/\s+/g," ").trim()}
  function clearHighlight(container){container.querySelectorAll("mark.reader-evidence-highlight").forEach(mark=>mark.replaceWith(document.createTextNode(mark.textContent)));container.normalize()}
  function referenceParts(reference){return reference.split(/\s*(?:\.{3,}|…|\/)\s*/).map(normalize).filter(part=>part.length>15).sort((a,b)=>b.length-a.length)}
  function textNodes(container){const walker=document.createTreeWalker(container,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.nodeValue.trim()?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT});const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);return nodes}
  function wrapNode(node,start,end){const range=document.createRange();range.setStart(node,start);range.setEnd(node,end);const mark=document.createElement("mark");mark.className="reader-evidence-highlight";range.surroundContents(mark);return mark}
  function exactMatch(container,reference){
    const parts=referenceParts(reference);
    for(const node of textNodes(container)){
      const mapped=normalizedWithMap(node.nodeValue);
      for(const part of parts){const index=mapped.text.indexOf(part);if(index!==-1){const start=mapped.map[index],end=(mapped.map[index+part.length-1]||start)+1;return wrapNode(node,start,end)}}
    }
    return null;
  }
  function fuzzyMatch(container,reference){
    const wanted=new Set(normalize(reference).split(" ").filter(word=>word.length>3));if(!wanted.size)return null;
    let best=null;
    for(const node of textNodes(container)){
      const regex=/[^.!?]+[.!?]?/g;let match;
      while((match=regex.exec(node.nodeValue))){const words=new Set(normalize(match[0]).split(" ").filter(word=>word.length>3));let overlap=0;wanted.forEach(word=>{if(words.has(word))overlap++});const score=overlap/Math.max(1,Math.min(wanted.size,words.size));if(!best||score>best.score)best={node,start:match.index,end:match.index+match[0].length,score}}
    }
    return best&&best.score>=.34?wrapNode(best.node,best.start,best.end):null;
  }
  function highlight(review,scroll){
    passages.forEach(passage=>clearHighlight(passage));
    const passage=passages.find(item=>item.dataset.passageSection===review.dataset.sectionId);if(!passage)return null;
    const reference=review.dataset.reference||"";if(!reference){setEvidenceStatus("No evidence sentence attached");return null}
    const mark=exactMatch(passage,reference)||fuzzyMatch(passage,reference);
    setEvidenceStatus(mark?"Evidence highlighted for this question":"Reference shown with the answer");
    if(mark&&scroll)mark.scrollIntoView({behavior:"smooth",block:"center"});
    return mark;
  }
  function show(index,scrollEvidence,scrollReview){
    current=Math.max(0,Math.min(index,reviews.length-1));const review=reviews[current];
    reviews.forEach((item,i)=>item.classList.toggle("is-active",i===current));passages.forEach(item=>item.hidden=item.dataset.passageSection!==review.dataset.sectionId);nav.forEach((item,i)=>item.classList.toggle("is-current",i===current));
    previous.disabled=current===0;next.disabled=current===reviews.length-1;highlight(review,!!scrollEvidence);
    const button=review.querySelector(".reader-show-evidence");if(button)button.onclick=()=>{const mark=highlight(review,true);if(!mark){button.classList.add("is-unmatched");button.textContent="Evidence sentence not matched"}};
    nav[current]?.scrollIntoView({behavior:"smooth",block:"nearest",inline:"center"});if(scrollReview)review.scrollIntoView({behavior:"smooth",block:"start"});
  }
  nav.forEach(button=>button.addEventListener("click",()=>show(Number(button.dataset.reviewTarget),false,true)));
  previous.addEventListener("click",()=>show(current-1,false,true));next.addEventListener("click",()=>show(current+1,false,true));
  document.addEventListener("keydown",event=>{if(event.key==="ArrowRight"&&current<reviews.length-1)show(current+1,false,true);if(event.key==="ArrowLeft"&&current>0)show(current-1,false,true)});
  /* Number, Previous, and Next controls are authoritative. An intersection
     observer used to change `current` again while smooth scrolling, which
     could land users on a neighbouring question. */
  show(0,false,false);
})();
