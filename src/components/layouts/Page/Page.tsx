import type { ReactNode } from 'react';

import './Page.css';

interface PageProps {
  children: ReactNode;
  className?: string;
}

function Page({ children, className = '' }: PageProps) {
  return (
    <main className={`page ${className}`}>
      <div className="page__content">{children}</div>
    </main>
  );
}

export default Page;
