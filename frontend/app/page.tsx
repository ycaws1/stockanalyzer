'use client';

import { useState } from 'react';
import Dashboard from '../components/Dashboard';
import TradeSimulator from '../components/TradeSimulator';
import NavBar from '../components/NavBar';

export default function Home() {
    const [activeTab, setActiveTab] = useState<'market' | 'trade'>('market');

    return (
        <main style={{ paddingBottom: '80px' }}>
            {activeTab === 'market' ? (
                <Dashboard />
            ) : (
                <div className="container" style={{ paddingTop: '2rem' }}>
                    <h1 style={{ marginBottom: '1rem' }}>Trade Simulator</h1>
                    <TradeSimulator />
                </div>
            )}
            <NavBar activeTab={activeTab} onTabChange={setActiveTab} />
        </main>
    );
}
