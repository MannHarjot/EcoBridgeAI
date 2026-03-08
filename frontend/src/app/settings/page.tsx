'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useSession } from '@/context/SessionContext';
import { getVoices } from '@/lib/api';
import type { ImpairmentMode, OutputMode, Voice } from '@/lib/types';
import ModeIndicator from '@/components/ModeIndicator';

const MODES: { value: ImpairmentMode; label: string; desc: string }[] = [
  { value: 'dual_impairment', label: 'Dual impairment',   desc: 'Speech and hearing support' },
  { value: 'hearing_only',   label: 'Hearing impairment', desc: 'Captions + text output' },
  { value: 'speech_only',    label: 'Speech impairment',  desc: 'Voice output + predictions' },
];

const OUTPUT_MODES: { value: OutputMode; label: string }[] = [
  { value: 'text_only',      label: 'Text only' },
  { value: 'text_and_voice', label: 'Text + Voice' },
  { value: 'voice_only',     label: 'Voice only' },
  { value: 'visual_only',    label: 'Visual only' },
];

export default function SettingsPage() {
  const { preferences, updatePreferences } = useSession();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getVoices()
      .then(setVoices)
      .catch(() => {
        // Backend not reachable — show empty
      });
  }, []);

  const handleSave = async () => {
    await updatePreferences(preferences);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <main className="flex flex-col min-h-screen bg-navy">
      {/* Header */}
      <header className="flex items-center gap-4 px-4 py-4 border-b border-slate-700/50 bg-slate-900/80 sticky top-0 z-10">
        <Link
          href="/"
          className="p-2 rounded-xl text-slate-400 hover:text-warm-white hover:bg-slate-800/60 transition-colors min-h-[0]"
          aria-label="Back"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-warm-white">Settings</h1>
          <p className="text-base text-slate-400">Accessibility preferences</p>
        </div>
        <button
          onClick={handleSave}
          className={[
            'px-4 py-2 rounded-xl text-lg font-semibold transition-all min-h-[0]',
            saved
              ? 'bg-emerald-600 text-white'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white',
          ].join(' ')}
        >
          {saved ? '✓ Saved' : 'Save'}
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-8 max-w-lg mx-auto w-full">

        {/* Impairment mode */}
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-warm-white">Impairment mode</h2>
          <div className="space-y-2">
            {MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => updatePreferences({ preferred_mode: m.value })}
                className={[
                  'w-full min-h-[64px] px-4 py-3 rounded-2xl border text-left',
                  'flex items-center gap-3 transition-all active:scale-[0.99]',
                  preferences.preferred_mode === m.value
                    ? 'bg-indigo-600/20 border-indigo-500/60 text-warm-white'
                    : 'bg-slate-800/60 border-slate-700/40 text-slate-300 hover:border-slate-600',
                ].join(' ')}
              >
                <ModeIndicator mode={m.value} compact />
                <div>
                  <p className="text-lg font-medium">{m.label}</p>
                  <p className="text-sm text-slate-400">{m.desc}</p>
                </div>
                {preferences.preferred_mode === m.value && (
                  <span className="ml-auto text-indigo-400">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" />
                    </svg>
                  </span>
                )}
              </button>
            ))}
          </div>
        </section>

        {/* Output mode */}
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-warm-white">Output mode</h2>
          <div className="grid grid-cols-2 gap-2">
            {OUTPUT_MODES.map((om) => (
              <button
                key={om.value}
                onClick={() => updatePreferences({})}
                className={[
                  'min-h-[56px] px-3 py-3 rounded-2xl border text-lg font-medium',
                  'transition-all active:scale-[0.98]',
                  'bg-slate-800/60 border-slate-700/40 text-slate-300 hover:border-slate-600',
                ].join(' ')}
              >
                {om.label}
              </button>
            ))}
          </div>
        </section>

        {/* Voice selection */}
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-warm-white">Voice</h2>
          {voices.length === 0 ? (
            <p className="text-base text-slate-500 p-4 rounded-2xl bg-slate-800/40 border border-slate-700/40">
              Connect the backend to browse available voices.
            </p>
          ) : (
            <div className="space-y-2">
              {voices.map((v) => (
                <button
                  key={v.voice_id}
                  onClick={() => updatePreferences({ voice_id: v.voice_id })}
                  className={[
                    'w-full min-h-[60px] px-4 py-3 rounded-2xl border text-left',
                    'flex items-center gap-3 transition-all active:scale-[0.99]',
                    preferences.voice_id === v.voice_id
                      ? 'bg-indigo-600/20 border-indigo-500/60'
                      : 'bg-slate-800/60 border-slate-700/40 hover:border-slate-600',
                  ].join(' ')}
                >
                  <span className="text-xl">🎙</span>
                  <div className="flex-1">
                    <p className="text-lg font-medium text-warm-white">{v.name}</p>
                    {v.description && (
                      <p className="text-sm text-slate-400">{v.description}</p>
                    )}
                  </div>
                  {v.recommended && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      Recommended
                    </span>
                  )}
                  {preferences.voice_id === v.voice_id && (
                    <span className="text-indigo-400">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" />
                      </svg>
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Language */}
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-warm-white">Language</h2>
          <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 space-y-2">
            <label htmlFor="language" className="text-base text-slate-300">
              Speech recognition & output language
            </label>
            <select
              id="language"
              value={preferences.language}
              onChange={(e) => updatePreferences({ language: e.target.value })}
              className="w-full bg-slate-900 border border-slate-600 text-warm-white rounded-xl px-3 py-2 text-lg focus:border-indigo-500 outline-none"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="pt">Português</option>
              <option value="ar">العربية</option>
              <option value="zh">中文</option>
            </select>
          </div>
        </section>

        {/* Emergency info */}
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-warm-white">Emergency info</h2>
          <p className="text-base text-slate-400">
            Shown to responders when the emergency button is activated.
          </p>
          <div className="p-4 rounded-2xl bg-slate-800/60 border border-rose-800/30 space-y-3">
            {[
              { key: 'name',              label: 'Full name',           type: 'text',  placeholder: 'Your name' },
              { key: 'condition',         label: 'Medical condition',   type: 'text',  placeholder: 'e.g. non-verbal autism' },
              { key: 'emergency_contact', label: 'Emergency contact',   type: 'tel',   placeholder: '+1 555 000 0000' },
              { key: 'allergies',         label: 'Allergies',           type: 'text',  placeholder: 'e.g. penicillin, nuts' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key} className="space-y-1">
                <label htmlFor={`emerg-${key}`} className="text-sm text-slate-400 font-medium">
                  {label}
                </label>
                <input
                  id={`emerg-${key}`}
                  type={type}
                  placeholder={placeholder}
                  value={(preferences.emergency_info[key] as string) ?? ''}
                  onChange={(e) =>
                    updatePreferences({
                      emergency_info: {
                        ...preferences.emergency_info,
                        [key]: e.target.value,
                      },
                    })
                  }
                  className="w-full bg-slate-900 border border-slate-600 text-warm-white rounded-xl px-3 py-2 text-lg focus:border-rose-500 outline-none placeholder-slate-600"
                />
              </div>
            ))}
          </div>
        </section>

        {/* About */}
        <section className="pb-8 text-center space-y-1">
          <p className="text-base text-slate-500">EchoBridge AI · v0.1.0</p>
          <p className="text-sm text-slate-600">
            Built for accessibility · Powered by Backboard AI
          </p>
        </section>
      </div>
    </main>
  );
}
