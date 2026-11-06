import './WaitersGoal.css';
import { GoalIcon, GoalOverlay } from 'src/assets/icons';

type WaitersGoalProps = {
  name: string;
  goal: string;
  sum: number;
  need: number;
  expanded: boolean;
};

const WaitersGoal = ({ name, goal, sum, expanded, need }: WaitersGoalProps) => {
  return (
    <div className={`waiters-goal ${expanded ? 'expanded' : ''}`}>
      <GoalOverlay className={'goal-overlay'} />
      <div className={'goal-info'}>
        <div className={'goal-icon'}>
          <GoalIcon />
        </div>
        <div className={'goal-body'}>
          <span className={'goal-body__name'}>Цель {name}</span>
          <span className={'goal-body__goal'}>{goal}</span>
        </div>
        <div className={'goal-percentage'}>{(sum / need) * 100} %</div>
      </div>
      <div className={'progress'}>
        <div className={'progress-bar'} style={{ width: `calc(${(sum / need) * 100}%)` }} />
      </div>
    </div>
  );
};

export default WaitersGoal;
