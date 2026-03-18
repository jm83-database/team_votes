"""
Azure Cosmos DB Service for Team Votes System
Handles all database operations with JSON fallback for local development
"""

import os
import json
import datetime
from typing import List, Dict, Any
from threading import RLock

try:
    from azure.cosmos import CosmosClient
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False
    print("Warning: azure-cosmos not installed. Using local JSON fallback.")


class CosmosService:
    def __init__(self):
        self.data_lock = RLock()
        self.use_cosmos = False
        self.container = None
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)

        if COSMOS_AVAILABLE and self._has_cosmos_credentials():
            try:
                self._init_cosmos_db()
                self.use_cosmos = True
                print("Cosmos DB initialized for team votes")
            except Exception as e:
                print(f"Failed to initialize Cosmos DB: {e}. Using JSON fallback.")

    def _has_cosmos_credentials(self) -> bool:
        return all([
            os.environ.get('COSMOS_ENDPOINT'),
            os.environ.get('COSMOS_KEY'),
            os.environ.get('COSMOS_DB'),
            os.environ.get('COSMOS_CONTAINER')
        ])

    def _init_cosmos_db(self):
        client = CosmosClient(
            os.environ['COSMOS_ENDPOINT'],
            credential=os.environ['COSMOS_KEY']
        )
        database = client.get_database_client(os.environ['COSMOS_DB'])
        self.container = database.get_container_client(os.environ['COSMOS_CONTAINER'])

    # ========== GENERIC COSMOS/JSON OPERATIONS ==========

    def _load_cosmos(self, doc_id: str, partition_key: str, data_field: str = 'data') -> Any:
        try:
            doc = self.container.read_item(item=doc_id, partition_key=partition_key)
            return doc.get(data_field, [])
        except Exception:
            return []

    def _save_cosmos(self, doc_id: str, partition_key: str, data: Any,
                     doc_type: str, data_field: str = 'data') -> bool:
        try:
            doc = {
                "id": doc_id,
                "cohort_id": partition_key,
                "type": doc_type,
                data_field: data,
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
            try:
                self.container.replace_item(item=doc_id, body=doc)
            except Exception:
                self.container.create_item(body=doc)
            return True
        except Exception as e:
            print(f"Cosmos save error ({doc_id}): {e}")
            return False

    def _load_json(self, filepath: str) -> Any:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"JSON load error ({filepath}): {e}")
            return []

    def _save_json(self, filepath: str, data: Any) -> bool:
        try:
            with self.data_lock:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"JSON save error ({filepath}): {e}")
            return False

    # ========== COHORTS ==========

    def load_cohorts(self) -> List[Dict[str, Any]]:
        if self.use_cosmos:
            return self._load_cosmos("team_votes_cohorts", "system")
        return self._load_json(os.path.join(self.data_dir, 'cohorts.json'))

    def save_cohorts(self, cohorts: List[Dict[str, Any]]) -> bool:
        if self.use_cosmos:
            return self._save_cosmos("team_votes_cohorts", "system", cohorts, "cohorts")
        return self._save_json(os.path.join(self.data_dir, 'cohorts.json'), cohorts)

    # ========== STUDENTS (per cohort) ==========

    def load_students(self, cohort_id: str) -> List[Dict[str, Any]]:
        if self.use_cosmos:
            return self._load_cosmos(f"{cohort_id}_students", cohort_id)
        return self._load_json(os.path.join(self.data_dir, f'{cohort_id}_students.json'))

    def save_students(self, cohort_id: str, students: List[Dict[str, Any]]) -> bool:
        if self.use_cosmos:
            return self._save_cosmos(f"{cohort_id}_students", cohort_id, students, "students")
        return self._save_json(os.path.join(self.data_dir, f'{cohort_id}_students.json'), students)

    # ========== TEAMS (per cohort) ==========

    def load_teams(self, cohort_id: str) -> List[Dict[str, Any]]:
        if self.use_cosmos:
            return self._load_cosmos(f"{cohort_id}_teams", cohort_id)
        return self._load_json(os.path.join(self.data_dir, f'{cohort_id}_teams.json'))

    def save_teams(self, cohort_id: str, teams: List[Dict[str, Any]]) -> bool:
        if self.use_cosmos:
            return self._save_cosmos(f"{cohort_id}_teams", cohort_id, teams, "teams")
        return self._save_json(os.path.join(self.data_dir, f'{cohort_id}_teams.json'), teams)

    # ========== VOTES (per cohort) ==========

    def load_votes(self, cohort_id: str) -> List[Dict[str, Any]]:
        if self.use_cosmos:
            return self._load_cosmos(f"{cohort_id}_votes", cohort_id)
        return self._load_json(os.path.join(self.data_dir, f'{cohort_id}_votes.json'))

    def save_votes(self, cohort_id: str, votes: List[Dict[str, Any]]) -> bool:
        if self.use_cosmos:
            return self._save_cosmos(f"{cohort_id}_votes", cohort_id, votes, "votes")
        return self._save_json(os.path.join(self.data_dir, f'{cohort_id}_votes.json'), votes)

    # ========== VOTE CONFIG (per cohort) ==========

    def load_vote_config(self, cohort_id: str) -> Dict[str, Any]:
        if self.use_cosmos:
            result = self._load_cosmos(f"{cohort_id}_vote_config", cohort_id)
            if isinstance(result, dict):
                return result
            return {}
        result = self._load_json(os.path.join(self.data_dir, f'{cohort_id}_vote_config.json'))
        if isinstance(result, dict):
            return result
        return {}

    def save_vote_config(self, cohort_id: str, config: Dict[str, Any]) -> bool:
        if self.use_cosmos:
            return self._save_cosmos(f"{cohort_id}_vote_config", cohort_id, config, "vote_config")
        return self._save_json(os.path.join(self.data_dir, f'{cohort_id}_vote_config.json'), config)

    # ========== DELETE COHORT DATA ==========

    def delete_cohort_data(self, cohort_id: str) -> bool:
        doc_ids = [
            f"{cohort_id}_students",
            f"{cohort_id}_teams",
            f"{cohort_id}_votes",
            f"{cohort_id}_vote_config",
        ]
        if self.use_cosmos:
            for doc_id in doc_ids:
                try:
                    self.container.delete_item(item=doc_id, partition_key=cohort_id)
                except Exception:
                    pass
        else:
            for doc_id in doc_ids:
                filepath = os.path.join(self.data_dir, f'{doc_id}.json')
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"JSON delete error ({filepath}): {e}")
        return True
