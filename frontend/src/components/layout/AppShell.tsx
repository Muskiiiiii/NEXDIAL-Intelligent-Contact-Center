import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';

import { OverviewPage } from '../../pages/OverviewPage';
import { LiveOperationsPage } from '../../pages/LiveOperationsPage';
import { CampaignsPage } from '../../pages/CampaignsPage';
import { AgentManagementPage } from '../../pages/AgentManagementPage';
import { BorrowerQueuePage } from '../../pages/BorrowerQueuePage';
import { CallHistoryPage } from '../../pages/CallHistoryPage';
import { PredictiveEnginePage } from '../../pages/PredictiveEnginePage';
import { SafetyControllerPage } from '../../pages/SafetyControllerPage';
import { ProviderHealthPage } from '../../pages/ProviderHealthPage';
import { SimulationLabPage } from '../../pages/SimulationLabPage';
import { FailureInjectionPage } from '../../pages/FailureInjectionPage';
import { AnalyticsPage } from '../../pages/AnalyticsPage';
import { SystemArchitecturePage } from '../../pages/SystemArchitecturePage';
import { SettingsPage } from '../../pages/SettingsPage';

export const AppShell: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);

  const renderContent = () => {
    switch (currentTab) {
      case 'overview':
        return <OverviewPage />;
      case 'live-operations':
        return <LiveOperationsPage />;
      case 'campaigns':
        return <CampaignsPage />;
      case 'agents':
        return <AgentManagementPage />;
      case 'borrowers':
        return <BorrowerQueuePage />;
      case 'calls':
        return <CallHistoryPage />;
      case 'predictive':
        return <PredictiveEnginePage />;
      case 'safety':
        return <SafetyControllerPage />;
      case 'providers':
        return <ProviderHealthPage />;
      case 'simulation':
        return <SimulationLabPage />;
      case 'failures':
        return <FailureInjectionPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'architecture':
        return <SystemArchitecturePage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <div className="min-h-screen bg-background text-text flex">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main View Area */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${
          isSidebarCollapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        {/* Top Navigation */}
        <TopNav isSidebarCollapsed={isSidebarCollapsed} />

        {/* Dynamic Content Container */}
        <main className="flex-1 mt-16 p-6 overflow-y-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};
