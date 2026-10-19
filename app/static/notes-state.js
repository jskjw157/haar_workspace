(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.NoteState=api;})(typeof globalThis!=='undefined'?globalThis:this,()=>{
  class NoteSession {
    constructor(save,onState,uuid=()=>crypto.randomUUID()){this.save=save;this.onState=onState;this.uuid=uuid;this.dirty=false;this.saving=false;this.conflict=false;this.invalid=false;this.error=null;this.pending=null;this.generation=0;}
    load(page){this.pageId=page.id;this.revision=page.revision;this.updatedAt=page.updated_at;this.value=structuredClone({title:page.title,blocks:page.blocks});this.dirty=false;this.conflict=false;this.invalid=false;this.error=null;this.pending=null;this.generation++;this.emit();}
    edit(value){this.value=structuredClone(value);this.generation++;this.dirty=true;if(!this.conflict){this.error=null;this.invalid=false;}this.emit();}
    emit(){this.onState(this);}
    async flush(){
      if(this.saving||this.conflict||this.invalid||!this.dirty)return !this.dirty;
      if(!this.pending)this.pending={generation:this.generation,request:{page_id:this.pageId,expected_revision:this.revision,...structuredClone(this.value),idempotency_key:this.uuid()}};
      const pending=this.pending;this.saving=true;this.emit();
      try{const receipt=await this.save(pending.request);this.revision=receipt.revision;this.updatedAt=receipt.updated_at;this.pending=null;this.error=null;this.dirty=this.generation!==pending.generation;}
      catch(e){this.error=e;this.conflict=e.status===409;this.invalid=!!e.status&&e.status>=400&&e.status<500&&e.status!==409&&e.status!==429;if(this.invalid)this.pending=null;}
      finally{this.saving=false;this.emit();}
      if(this.dirty&&!this.error)return this.flush();
      return !this.dirty;
    }
  }
  return {NoteSession};
});
