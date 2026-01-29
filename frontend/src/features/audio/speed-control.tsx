'use client'

import { Select } from '@/components/ui/select';

export interface SpeedControlProps {
  rate: number;
  onChange: (rate: number) => void;
  disabled?: boolean;
}

const SPEED_OPTIONS = [0.75, 1, 1.25, 1.5, 2];

export function SpeedControl({ rate, onChange, disabled = false }: SpeedControlProps) {
  const options = SPEED_OPTIONS.map((value) => ({
    value: String(value),
    label: `${value}x`,
  }));

  return (
    <Select
      label="Vitesse"
      options={options}
      value={String(rate)}
      onChange={(event) => onChange(Number(event.target.value))}
      disabled={disabled}
    />
  );
}
