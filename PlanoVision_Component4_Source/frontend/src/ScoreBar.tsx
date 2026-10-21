export function scoreBand(value:number,actionRequired:boolean,profit:number):'red'|'yellow'|'green'{
  if(profit<0||value<50)return 'red';
  if(actionRequired||value<80)return 'yellow';
  return 'green';
}

export default function ScoreBar({value,actionRequired,profit}:{value:number;actionRequired:boolean;profit:number}){
  const score=Math.min(100,Math.max(0,value));
  const band=scoreBand(score,actionRequired,profit);
  return <><div className={'score-number band-'+band}>{score.toFixed(1)}<small> / 100 points</small></div><div className={'score-meter band-'+band} role="progressbar" aria-label="Experimental financial planning score" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}><div className="score-fill" style={{width:score+'%'}}/></div><div className="score-ticks"><span>0</span><span>50</span><span>80</span><span>100</span></div><p className="score-legend"><span className="legend-red">Red: loss or &lt;50</span> · <span className="legend-yellow">Yellow: rule breach or &lt;80</span> · <span className="legend-green">Green: ≥80 and rules pass</span></p><p className="muted">Experimental UI warning bands—not calibrated financial-risk categories.</p></>;
}
