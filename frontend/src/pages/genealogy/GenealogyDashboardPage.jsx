import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/api/index.js';
import { Link } from 'react-router-dom';
import { DocumentPlusIcon, ClockIcon, AcademicCapIcon, InboxIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

// GedcomUpload Component: Handles the file selection and upload logic.
const GedcomUpload = ({ onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const fileInputRef = useRef(null); // To reset the file input field after upload

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError('');
            setSuccessMessage('');
        } else {
            setFile(null);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            setError('Please select a GEDCOM file (.ged) to upload.');
            return;
        }
        setIsUploading(true);
        setError('');
        setSuccessMessage('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await apiClient.post('/genealogy/trees/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setSuccessMessage(`Family tree "${response.data.file_name}" (ID: ${response.data.id}) was uploaded and parsed successfully!`);
            onUploadSuccess(); // Callback to refresh the tree list in the parent component
            setFile(null); // Clear the selected file state
            if (fileInputRef.current) {
                 fileInputRef.current.value = ''; // Visually reset the file input field
            }
        } catch (err) {
            const errorDetail = err.response?.data?.detail || 'Upload failed. Please ensure it is a valid .ged file and try again.';
            setError(errorDetail);
            console.error("GEDCOM Upload error:", err);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-700 mb-4 border-b border-gray-200 pb-3">
                <DocumentPlusIcon className="h-6 w-6 inline mr-2 text-blue-600" />
                Upload New Family Tree
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="gedcom-file-input" className="block text-sm font-medium text-gray-700 mb-1">
                        Select GEDCOM file (`.ged` format only)
                    </label>
                    <input 
                        type="file" 
                        id="gedcom-file-input"
                        ref={fileInputRef}
                        onChange={handleFileChange} 
                        accept=".ged,text/gedcom,application/gcom" // Common MIME types for GEDCOM
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border file:border-gray-300 file:text-sm file:font-semibold file:bg-slate-50 file:text-blue-700 hover:file:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>
                {error && <p className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">{error}</p>}
                {successMessage && <p className="text-green-600 text-sm bg-green-50 p-3 rounded-md border border-green-200">{successMessage}</p>}
                <div className="text-right pt-2">
                    <button 
                        type="submit" 
                        disabled={!file || isUploading}
                        className="inline-flex items-center justify-center py-2 px-6 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                        <DocumentPlusIcon className="h-5 w-5 mr-2" />
                        {isUploading ? 'Uploading...' : 'Upload File'}
                    </button>
                </div>
            </form>
        </div>
    );
};

// Main Dashboard Page Component
const GenealogyDashboardPage = () => {
    const [trees, setTrees] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [pageError, setPageError] = useState('');

    const fetchTrees = useCallback(async (showLoadingSpinner = true) => {
        if(showLoadingSpinner) setIsLoading(true);
        setPageError('');
        try {
            const response = await apiClient.get('/genealogy/trees');
            setTrees(response.data);
        } catch (err) {
            setPageError('Failed to load your family trees. Please try refreshing the page or check your connection.');
            console.error("Failed to fetch family trees:", err);
        } finally {
            if(showLoadingSpinner) setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTrees();
    }, [fetchTrees]);

    return (
        <div className="space-y-8">
            <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <AcademicCapIcon className="h-10 w-10 text-blue-600 flex-shrink-0" />
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Genealogy Dashboard</h1>
                        <p className="text-sm text-gray-500 mt-1">Manage your family trees and initiate AI-powered research to uncover your history.</p>
                    </div>
                </div>
                <button
                    onClick={() => fetchTrees(true)}
                    disabled={isLoading}
                    className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 self-start sm:self-center transition-colors"
                    title="Refresh tree list"
                >
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>

            <GedcomUpload onUploadSuccess={() => fetchTrees(false)} /> {/* Refresh list without full page load effect */}
            
            {pageError && (
                <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md my-4" role="alert">
                    <p className="font-bold">Error Loading Trees</p>
                    <p>{pageError}</p>
                </div>
            )}

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h2 className="text-xl font-semibold text-gray-700 mb-4 border-b border-gray-200 pb-3">My Family Trees</h2>
                {isLoading ? (
                    <div className="text-center py-8 text-gray-500">
                        <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-500"/>
                        Loading your family trees...
                    </div>
                ) : trees.length > 0 ? (
                    <ul className="divide-y divide-gray-200">
                        {trees.map(tree => (
                            <li key={tree.id}>
                                <Link to={`/genealogy/trees/${tree.id}`} className="block p-4 hover:bg-slate-50 transition-colors duration-150 ease-in-out group">
                                    <div className="flex items-center justify-between gap-4 flex-wrap">
                                        <div>
                                            <p className="text-md sm:text-lg font-medium text-blue-600 group-hover:text-blue-700 group-hover:underline">{tree.file_name}</p>
                                            <p className="text-xs text-gray-500 mt-0.5">Tree ID: {tree.id}</p>
                                        </div>
                                        <div className="flex items-center text-xs sm:text-sm text-gray-500 flex-shrink-0">
                                            <ClockIcon className="h-4 w-4 mr-1.5 text-gray-400" />
                                            Uploaded: {format(new Date(tree.created_at), 'PP')}
                                        </div>
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <div className="text-center py-10">
                        <InboxIcon className="h-12 w-12 text-gray-400 mx-auto mb-3"/>
                        <p className="text-lg text-gray-600">No family trees have been uploaded yet.</p>
                        <p className="text-sm text-gray-500 mt-1">Use the form above to upload your first GEDCOM (.ged) file to begin.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default GenealogyDashboardPage;