'use client';

import { useEffect, useState } from 'react';

interface Props {
  message: string | null;
}

export default function PacingAlert({ message }: Props) {
  const [visible, setVisible] = useState(false);
  const [displayMsg, setDisplayMsg] = useState('');

  useEffect(() => {
    if (message) {
      setDisplayMsg(message);
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [message]);

  if (!displayMsg) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={[
        'flex items-center gap-3 px-4 py-3',
        'bg-amber-500/15 border-b border-amber-500/30 border-l-4 border-l-amber-500',
        'animate-slide-down transition-opacity duration-500',
        visible ? 'opacity-100' : 'opacity-0',
      ].join(' ')}
    >
      <span className="text-amber-400 text-xl flex-shrink-0" aria-hidden="true">
        ⚡
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-base text-amber-300 font-medium leading-snug">
          {displayMsg}
        </p>
        <p className="text-sm text-amber-400/60 mt-0.5">
          You can ask them to slow down using the prediction tiles below.
        </p>
      </div>

      <span className="text-amber-400/50 text-sm flex-shrink-0 font-mono">
        Pacing
      </span>
    </div>
  );
}
