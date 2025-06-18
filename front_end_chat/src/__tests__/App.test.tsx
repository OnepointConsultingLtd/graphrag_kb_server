import { test } from 'vitest';
import { render } from '@testing-library/react';
import App from '../App';

test('App renders without crashing', () => {
    render(<App />);
    // Add your test assertions here
});
