export const number=(x:number,d=4)=>x.toFixed(d);export const shortHash=(s:string)=>s.slice(0,18)+'…';
export const time=(iso:string)=>{if(!iso)return '';try{return new Date(iso).toLocaleString('zh-CN',{hour12:false})}catch{return iso}};
