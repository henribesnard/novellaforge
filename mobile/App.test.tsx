import React from 'react';
import { render, screen } from '@testing-library/react-native';
import App from './App';

describe('App', () => {
    it('renders correctly', () => {
        render(<App />);
        expect(screen.getByText('Welcome to NovellaForge Mobile!')).toBeOnTheScreen();
    });
});
