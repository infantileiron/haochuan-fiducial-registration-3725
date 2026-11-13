import csv,io
from fastapi import HTTPException
from src.models.entities import Report
from src.config.settings import ARTIFACT_DIR
from src.utils import repository as repo
from src.utils.identity import new_id,now
from src.constants.enums import ReportStatus


def safe_cell(v):return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v
def list_reports():return repo.all_rows('reports')


def create(data):
    # 与审批/撤销互斥：报告生成瞬间以“仍有效”的批准为准，并绑定该次决定。
    with repo.transaction() as (conn,q):
        run=repo.tx_get(conn,q,'runs',data.run_id)
        review=repo.tx_get(conn,q,'reviews',data.review_id)
        if review['run_id']!=run['id'] or run['status']!='completed':
            raise ValueError('报告必须引用该运行的复核记录')
        if review['status']!='approved' or not review.get('effective_decision_id'):
            raise HTTPException(409,'报告只能基于当前仍有效的批准生成；批准已撤销请重新提审')
        decision_id=review['effective_decision_id']
        report=repo.tx_put(conn,q,'reports',Report(
            new_id('rpt'),data.run_id,data.review_id,data.title,now(),
            decision_id=decision_id,status=ReportStatus.ACTIVE.value,
        ))
    ARTIFACT_DIR.mkdir(parents=True,exist_ok=True)
    (ARTIFACT_DIR/(report['id']+'.csv')).write_text(_render(report),encoding='utf-8')
    return report


def download(id):
    report=repo.get('reports',id)
    if report.get('status',ReportStatus.ACTIVE.value)==ReportStatus.INVALID.value:
        raise HTTPException(403,'该报告已随批准撤销而失效，不能下载；请使用重新批准后出具的新报告')
    review=repo.get('reviews',report['review_id'])
    # 双保险：即使失效标记漏写，有效批准不存在同样拒绝下载。
    if review['status']!='approved' or not review.get('effective_decision_id'):
        raise HTTPException(403,'复核未通过或批准已撤销，报告停止下载')
    if report.get('decision_id') and report['decision_id']!=review.get('effective_decision_id'):
        raise HTTPException(403,'报告绑定的批准决定已失效，旧报告不随再次批准恢复')
    return _render(report)


def _render(report):
    run=repo.get('runs',report['run_id']);r=run['result'];review=repo.get('reviews',report['review_id'])
    out=io.StringIO();w=csv.writer(out)
    w.writerow(['report','report_status','decision_id','review_id','convention','source_frame','target_frame','unit','threshold_mm','seed','iterations','checksum'])
    w.writerow([safe_cell(report['title']),report.get('status','active'),report.get('decision_id',''),review['id'],r['convention'],safe_cell(r['frame']['source_frame']),safe_cell(r['frame']['target_frame']),'mm',r['threshold_mm'],r['seed'],r['iterations'],r['checksum']]);w.writerow([])
    for method in ['full','robust']:
        m=r[method];w.writerow([method,'det_R',m['det_R'],'rmse_all',m.get('rmse_all',m['rmse'])]);w.writerow(['R_11','R_12','R_13','t_mm'])
        for i in range(3):w.writerow(m['R'][i]+[m['t'][i]])
        if method=='robust':w.writerow(['inlier_count',m['inlier_count'],'rmse_inliers',m['rmse_inliers'],'refinement_stable',m['refinement_stable'],'best_sample_ids','|'.join(m['best_sample_ids'])])
    w.writerow([]);w.writerow(['id','sx_mm','sy_mm','sz_mm','tx_mm','ty_mm','tz_mm','full_residual_mm','robust_residual_mm','final_inlier'])
    for p in r['rows']:w.writerow([safe_cell(p['id'])]+p['source']+p['target']+[p['full_residual'],p['robust_residual'],p['inlier']])
    return '\ufeff'+out.getvalue()
