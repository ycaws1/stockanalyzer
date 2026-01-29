import React from 'react';
import styles from './NavBar.module.css';

interface NavBarProps {
    activeTab: 'market' | 'trade';
    onTabChange: (tab: 'market' | 'trade') => void;
}

export default function NavBar({ activeTab, onTabChange }: NavBarProps) {
    return (
        <nav className={styles.navbar}>
            <button
                className={`${styles.navItem} ${activeTab === 'market' ? styles.active : ''}`}
                onClick={() => onTabChange('market')}
            >
                <span className={styles.icon}>📈</span>
                <span>Market</span>
            </button>

            <button
                className={`${styles.navItem} ${activeTab === 'trade' ? styles.active : ''}`}
                onClick={() => onTabChange('trade')}
            >
                <span className={styles.icon}>🤝</span>
                <span>Trade</span>
            </button>
        </nav>
    );
}
