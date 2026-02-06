'use client';

import { useState } from 'react';
import Dashboard from '../components/Dashboard';
import TradeSimulator from '../components/TradeSimulator';
import NavBar from '../components/NavBar';
import NotificationHistory from '../components/NotificationHistory';

export default function Home() {
    const [activeTab, setActiveTab] = useState<'market' | 'trade' | 'notifications'>('market');

    const renderContent = () => {
        switch (activeTab) {
            case 'market':
                return <Dashboard />;
            case 'trade':
                return (
                    <div className="container" style={{ paddingTop: '2rem' }}>
                        <h1 style={{ marginBottom: '1rem' }}>Trade Simulator</h1>
                        <TradeSimulator />
                    </div>
                );
            case 'notifications':
                return <NotificationHistory />;
            default:
                return <Dashboard />;
        }
    };

    return (
        <main style={{ paddingBottom: '80px' }}>
            {renderContent()}
            <NavBar activeTab={activeTab} onTabChange={setActiveTab} />
        </main>
    );
}

