import requests
from config import config

class ApolloClient:
    def __init__(self):
        self.api_key = config.APOLLO_API_KEY
        self.base_url = "https://api.apollo.io/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.api_key
        }

    def search_contacts(self, domain, titles=None):
        """
        Search for contacts at a specific company domain.
        Titles defaults to looking for Founders, CEOs, or Marketing leaders.
        """
        if titles is None:
            titles = ["founder", "ceo", "marketing", "cmo", "influencer marketing"]
            
        url = f"{self.base_url}/mixed_people/api_search"
        payload = {
            "q_organization_domains": domain,
            "person_titles": titles,
            "page": 1,
            "per_page": 1 # We only need 1 top contact per company to maximize distinct companies
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            contacts = []
            for person in data.get('people', []):
                # We need to unlock the email if it's not present
                email = person.get('email')
                if not email and person.get('id'):
                     email = self._enrich_contact(person['id'])
                
                if email:
                    contacts.append({
                        "id": person.get("id"),
                        "name": f"{person.get('first_name')} {person.get('last_name')}",
                        "title": person.get('title'),
                        "email": email,
                        "linkedin_url": person.get('linkedin_url'),
                        "company": person.get('organization', {}).get('name')
                    })
            return contacts
        except Exception as e:
            print(f"Error searching contacts on Apollo for {domain}: {str(e)}")
            return []

    def _enrich_contact(self, person_id):
        """
        Unlock the contact's email address by their Apollo ID
        """
        url = f"{self.base_url}/people/match"
        payload = {
            "id": person_id
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get('person', {}).get('email')
        except Exception as e:
            print(f"Error enriching contact {person_id}: {str(e)}")
            return None
