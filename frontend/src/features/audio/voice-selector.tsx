'use client'

import { Select } from '@/components/ui/select';
import type { SpeechVoice } from '@/hooks/use-speech-synthesis';

export interface VoiceSelectorProps {
  voices: SpeechVoice[];
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export function VoiceSelector({ voices, value, onChange, disabled = false }: VoiceSelectorProps) {
  const options = voices.map((voice) => ({
    value: voice.id,
    label: `${voice.name} (${voice.lang})${voice.default ? ' *' : ''}`,
  }));

  return (
    <Select
      label="Voix"
      options={options.length ? options : [{ value: '', label: 'Voix indisponibles' }]}
      value={value ?? ''}
      onChange={(event) => onChange(event.target.value || null)}
      disabled={disabled || !options.length}
    />
  );
}
