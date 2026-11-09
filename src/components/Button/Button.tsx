import React from 'react';
import './Button.css';

type ButtonProps = {
  children: React.ReactNode;
  type?: 'primary' | 'secondary' | 'outline';
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
};

const Button: React.FC<ButtonProps> = ({ children, type, className, onClick, disabled }) => {
  const buttonType = type || 'primary';
  return (
    <button
      disabled={disabled}
      onClick={!disabled ? onClick : undefined}
      className={`button ${buttonType} ${className} ${disabled ? 'disabled' : ''}`}
    >
      {children}
    </button>
  );
};

export { Button };
