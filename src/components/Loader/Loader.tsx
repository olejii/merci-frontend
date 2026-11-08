import './Loader.css';

function Loader() {
  return (
    <div className={'loader-wrapper'}>
      <div className={'loader'} role="status" aria-label="Загрузка">
        <div className="loader__spinner" aria-hidden="true">
          <span />
        </div>
      </div>
    </div>
  );
}

export default Loader;
