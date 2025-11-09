import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { CreateUserModal } from './CreateUserModal';
import './UserSelector.css';

export const UserSelector: React.FC = () => {
  const { currentUser, users, setCurrentUser, refreshUsers } = useApp();
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleUserChange = (username: string) => {
    const user = users.find(u => u.username === username);
    setCurrentUser(user || null);
  };

  const handleUserCreated = async () => {
    await refreshUsers();
    setShowCreateModal(false);
  };

  return (
    <div className="user-selector">
      <select
        value={currentUser?.username || ''}
        onChange={(e) => handleUserChange(e.target.value)}
        className="user-select"
      >
        <option value="">Select User</option>
        {users.map(user => (
          <option key={user.username} value={user.username}>
            {user.display_name} (${user.balance.toFixed(2)})
          </option>
        ))}
      </select>
      <button
        onClick={() => setShowCreateModal(true)}
        className="btn-create-user"
        title="Create New User"
      >
        +
      </button>
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleUserCreated}
        />
      )}
    </div>
  );
};

