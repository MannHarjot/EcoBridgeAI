'use client';

import type { ConversationContext } from '@/lib/types';

interface Props {
  context: ConversationContext;
  className?: string;
}

const CONTEXT_CONFIG: Record<
  ConversationContext,
  { label: string; icon: string; badgeClass: string }
> = {
  medical:      { label: 'Medical',      icon: '🏥', badgeClass: 'badge-medical' },
  retail:       { label: 'Retail',       icon: '🛒', badgeClass: 'badge-retail' },
  emergency:    { label: 'Emergency',    icon: '🚨', badgeClass: 'badge-emergency' },
  casual:       { label: 'Casual',       icon: '💬', badgeClass: 'badge-casual' },
  professional: { label: 'Professional', icon: '💼', badgeClass: 'badge-professional' },
  unknown:      { label: 'Detecting…',   icon: '🔍', badgeClass: 'badge-unknown' },
};

export default function ContextBadge({ context, className = '' }: Props) {
  const config = CONTEXT_CONFIG[context] ?? CONTEXT_CONFIG.unknown;

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full',
        'text-sm font-medium border',
        config.badgeClass,
        className,
      ].join(' ')}
      aria-label={`Conversation context: ${config.label}`}
    >
      <span aria-hidden="true">{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
