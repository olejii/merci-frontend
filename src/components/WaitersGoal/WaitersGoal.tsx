import './WaitersGoal.css';
import { GoalIcon, GoalOverlay } from 'src/assets/icons';

type WaitersGoalProps = {
  name: string;
  goal: string;
  sum: number;
  need: number;
  amount?: number;
  mode: 'default' | 'expanded' | 'success';
  className?: string;
};

const WaitersGoal = ({
  name,
  goal,
  sum,
  mode = 'default',
  need,
  amount,
  className,
}: WaitersGoalProps) => {
  return (
    <div className={`waiters-goal ${className} ${mode === 'expanded' ? 'expanded' : ''}`}>
      <GoalOverlay className={'goal-overlay'} />
      <div className={'goal-info'}>
        <div className={'goal-icon'}>
          <GoalIcon />
        </div>
        <div className={'goal-body'}>
          <span className={'goal-body__name'}>
            {mode !== 'success' ? `Цель ${name}` : 'Вы приблизили цель'}
          </span>
          <span className={'goal-body__goal'}>{goal}</span>
        </div>
        <div className={'goal-percentage'}>
          {mode === 'success'
            ? '+' + Math.ceil((amount! / need) * 100)
            : Math.floor((sum / need) * 100)}{' '}
          %
        </div>
      </div>
      <div className={'progress'}>
        <div className={'progress-bar'} style={{ width: `calc(${(sum / need) * 100}%)` }} />
      </div>
      {mode !== 'default' ? (
        <div className={'progress-sum'}>
          <span>{new Intl.NumberFormat('ru').format(sum)} ₽</span> из{' '}
          {new Intl.NumberFormat('ru').format(need)} ₽
        </div>
      ) : null}
    </div>
  );
};

export default WaitersGoal;
