import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { BellAlertIcon, CheckCircleIcon, XCircleIcon, InformationCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

const SettingDisplayRow = ({ label, value, isEnabledOverall = true, comment = null }) => (
    <div className="py-3 sm:grid sm:grid-cols-3 sm:gap-4 items-center">
        <dt className="text-sm font-medium text-gray-600">{label}</dt>
        <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2 items-center">
            <div className="flex items-center">
                {typeof value === 'boolean' ? (
                    value && isEnabledOverall ? 
                        <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" /> : 
                        <XCircleIcon className="h-5 w-5 text-gray-400 mr-2 flex-shrink-0" />
                ) : null}
                <span className={!isEnabledOverall && typeof value !== 'boolean' ? 'text-gray-400 italic' : ''}>
                    {typeof value === 'boolean' ? (value && isEnabledOverall ? 'Enabled' : 'Disabled') : (value || <span className="italic text-gray-400">Not Set</span>)}
                </span>
            </div>
            {comment && isEnabledOverall && <p className="ml-4 text-xs text-gray-500 italic">{comment}</p>}
        </dd>
    </div>
);

const NotificationSettingsPanel = () => {
    const [settings, setSettings] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchSettings = useCallback(async (showLoadingSpinner = true) => {
        if (showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            const response = await apiClient.get('/admin/settings/notifications');
            setSettings(response.data);
        } catch (err) {
            setError('Failed to fetch notification settings. Ensure the backend is running and you have admin rights.');
            console.error("Fetch notification settings error:", err);
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    return (
        <div className="space-y-6">
            <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <BellAlertIcon className="h-7 w-7 text-blue-600" />
                    <h2 className="text-2xl font-semibold text-gray-800">Notification Settings</h2>
                </div>
                 <button onClick={() => fetchSettings(true)} disabled={isLoading} className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 transition-colors" title="Refresh settings">
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>
            {error && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert"><p>{error}</p></div>}

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <div className="bg-blue-50 border border-blue-200 p-4 rounded-md mb-6 flex items-start">
                    <InformationCircleIcon className="h-6 w-6 text-blue-500 mr-3 flex-shrink-0 mt-0.5"/>
                    <div>
                        <h4 className="text-sm font-semibold text-blue-800">Configuration Information</h4>
                        <p className="text-xs text-blue-700 mt-1">
                            This panel displays the current email notification configuration for agent tasks. 
                            To modify these settings, you must edit the <code className="bg-blue-200 text-blue-900 px-1 rounded font-mono">config/config.yml</code> file (for general preferences like recipient and event triggers) 
                            and the <code className="bg-blue-200 text-blue-900 px-1 rounded font-mono">backend/.env</code> file (for sensitive SMTP credentials). 
                            A restart of the backend service (<code className="bg-blue-200 text-blue-900 px-1 rounded font-mono">docker-compose restart backend</code>) is required for any changes to take effect.
                        </p>
                    </div>
                </div>

                {isLoading && !settings ? (
                     <p className="text-center py-8 text-gray-500">Loading notification settings...</p>
                ) : settings ? (
                    <dl className="divide-y divide-gray-200">
                        <SettingDisplayRow label="Overall Notifications System" value={settings.enabled} comment={settings.enabled ? "Email notifications are active." : "Email notifications are globally disabled."} />
                        <SettingDisplayRow label="Admin Recipient Email" value={settings.recipient_email} isEnabledOverall={settings.enabled} comment="Emails will be sent to this address." />
                        <SettingDisplayRow label="Notify on Task 'Awaits Review'" value={settings.notify_on?.awaits_review} isEnabledOverall={settings.enabled} />
                        <SettingDisplayRow label="Notify on Task 'Error'" value={settings.notify_on?.error} isEnabledOverall={settings.enabled} />
                        <SettingDisplayRow label="Notify on Task 'Applied'" value={settings.notify_on?.applied} isEnabledOverall={settings.enabled} />
                    </dl>
                ) : (
                     !error && <p className="text-sm text-gray-500 p-4 text-center">Notification settings are not currently available or configured.</p>
                )}
            </div>
             <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 text-xs text-gray-600">
                <p className="font-semibold">SMTP Server Details (from <code className="text-xs">backend/.env</code> - values not displayed for security):</p>
                <ul className="list-disc list-inside pl-4 mt-1">
                    <li><code className="text-xs">SMTP_HOST</code>, <code className="text-xs">SMTP_PORT</code>, <code className="text-xs">SMTP_USER</code>, <code className="text-xs">SMTP_PASSWORD</code>, <code className="text-xs">SMTP_SENDER_NAME</code></li>
                </ul>
                 <p className="mt-2">Ensure these are correctly set in your <code className="text-xs">backend/.env</code> file for email delivery to function when notifications are enabled.</p>
            </div>
        </div>
    );
};

export default NotificationSettingsPanel;