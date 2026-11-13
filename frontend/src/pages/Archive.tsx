import {useState} from 'react';
import * as reviews from '../api/reviews';
import * as reports from '../api/reports';
import * as runs from '../api/runs';
import {download} from '../api/client';
import {useResource} from '../hooks/useResource';
import {refreshResources} from '../stores/resources';
import {decisionLabels} from '../constants/enums';
import {time} from '../utils/format';
import PageTitle from '../components/common/PageTitle';
import Notice from '../components/common/Notice';
import StatusBadge from '../components/common/StatusBadge';
import type {User,Review,Report} from '../types/entities';

export default function Archive({user}:{user:User}){
  const{data:rv,error}=useResource(reviews.list,[] as Review[]);
  const{data:rp}=useResource(reports.list,[] as Report[]);
  const{data:rr}=useResource(runs.list,[]);
  const[id,setId]=useState(sessionStorage.getItem('fiducial-selected-run')||'run-demo');
  const[comment,setComment]=useState('已核查毫米轴系、detR、全量/稳健残差及最终内点，请工程师复核。');
  const[revokeReason,setRevokeReason]=useState<Record<string,string>>({});
  const[message,setMessage]=useState('');
  const reportDecision=new Map((rv.flatMap(r=>r.decisions||[])).map(d=>[d.id,d]));
  return <>
    <PageTitle chapter="06" title="把变换矩阵，连同离群依据归档" description="分析员提审，配准工程师复核。每次批准、退回与撤销均留痕并记录经办人；撤销批准后旧报告失效停发，重新提审通过另出新报告。"/>
    <Notice error={error||message}/>
    {user.role!=='viewer'&&<form className="paper form-grid" onSubmit={async e=>{e.preventDefault();try{await reviews.create({run_id:id,comment});refreshResources();setMessage('')}catch(e:any){setMessage(e.message)}}}>
      <label>完成的运行<select aria-label="完成的运行" value={id} onChange={e=>setId(e.target.value)}>{rr.filter(x=>x.status==='completed').map(x=><option key={x.id} value={x.id}>{x.id}</option>)}</select></label>
      <label>复核说明<textarea value={comment} onChange={e=>setComment(e.target.value)}/></label>
      <button className="primary">提交配准复核</button>
    </form>}

    <section className="paper">
      <h2>配准复核记录（含完整决定链）</h2>
      {rv.map(r=>{
        const decisions=r.decisions||[];
        return <article className="review-row" key={r.id}>
          <StatusBadge status={r.status}/>
          <div>
            <b>{r.run_id}</b><span className="mono"> · {r.id}</span>
            <p>{r.comment}</p>
            {r.status==='revoked'&&r.revoked_reason&&<p className="revoke-note">撤销原因：{r.revoked_reason}</p>}
            <small>{r.reviewer||'等待配准工程师复核'}</small>
            <table className="decision-table">
              <thead><tr><th>决定</th><th>意见 / 原因</th><th>经办人</th><th>时间</th><th>决定编号</th></tr></thead>
              <tbody>{decisions.map(d=><tr key={d.id}><td>{decisionLabels[d.action]||d.action}</td><td>{d.comment}</td><td>{d.actor}</td><td>{time(d.created_at)}</td><td className="mono">{d.id}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="actions">
            {user.role==='admin'&&r.status==='pending'&&['approved','rejected'].map(status=>
              <button key={status} onClick={async()=>{try{await reviews.decide(r.id,{status,comment:status==='approved'?'已核验毫米轴系、proper旋转、精炼稳定与最终内点，批准归档。':'请补充几何退化或精炼不稳定说明后重提。'});refreshResources()}catch(e:any){setMessage(e.message)}}}>{status==='approved'?'批准归档':'退回复查'}</button>)}
            {user.role==='admin'&&r.status==='approved'&&<>
              <label className="revoke-box">撤销原因（必填）<textarea aria-label="撤销原因" value={revokeReason[r.id]||''} onChange={e=>setRevokeReason(s=>({...s,[r.id]:e.target.value}))} placeholder="说明为何撤销该批准，将留档并使关联报告失效"/></label>
              <button className="danger" onClick={async()=>{try{const res=await reviews.revoke(r.id,(revokeReason[r.id]||'').trim());setMessage(`已撤销批准，${res.invalidated_reports} 份报告标记失效并停止下载`);refreshResources()}catch(e:any){setMessage(e.message)}}}>撤销批准</button>
            </>}
            {user.role!=='viewer'&&r.status==='approved'&&<button onClick={async()=>{try{await reports.create({title:'皓川光学标志点配准复核报告',run_id:r.run_id,review_id:r.id});refreshResources()}catch(e:any){setMessage(e.message)}}}>生成归档报告</button>}
          </div>
        </article>;
      })}
    </section>

    <section className="paper">
      <h2>归档报告（可追查对应决定）</h2>
      {rp.map(r=>{
        const invalid=(r.status||'active')==='invalid';
        const decision=reportDecision.get(r.decision_id||'');
        return <article className="record report-row" key={r.id}>
          <div>
            <b>{r.title}</b>
            <small>{r.run_id} · <span className="mono">{r.id}</span></small>
            <small>绑定决定：<span className="mono">{r.decision_id||'—'}</span>{decision?`（${decisionLabels[decision.action]||decision.action} · ${decision.actor} · ${time(decision.created_at)}）`:'（历史数据）'}</small>
            {invalid&&<small className="invalid-note">已失效：{r.invalid_reason||'批准已撤销'}；旧报告不随再次批准恢复，请查阅重新批准后出具的新报告。</small>}
          </div>
          <div className="actions">
            <StatusBadge status={r.status||'active'}/>
            {invalid
              ?<button disabled title="失效报告禁止下载">已停止下载</button>
              :<button onClick={()=>download('/reports/'+r.id+'/download','皓川标志点配准.csv').catch(e=>setMessage(e.message))}>下载配准证据 CSV ↓</button>}
          </div>
        </article>;
      })}
    </section>
  </>;
}
