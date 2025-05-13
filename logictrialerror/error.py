def service_selection_and_search(approved_services, details):
    """Function to handle both venue and vendor searches using separate agents with proper error handling"""
    print("\n=== Service Vendor Search ===")
    print("Let's find vendors for your approved services:")

    # Display services for selection
    for i, service in enumerate(approved_services, 1):
        print(f"{i}. {service['service']} (Budget: ₹{service['budget']:,})")

    # Ask user which service to find vendors for
    while True:
        search_vendors = input("\nWould you like to search for vendors for any of these services? (yes/no): ").lower()
        
        if search_vendors != "yes":
            break
            
        try:
            service_num = int(input("Enter the number of the service you'd like to find vendors for: "))
            if 1 <= service_num <= len(approved_services):
                selected_service = approved_services[service_num-1]
                
                print(f"\nSearching for {selected_service['service']} vendors matching your requirements...")
                print("This might take a few minutes as we search multiple sources...")
                
                # Choose the appropriate agent and task based on the selected service
                if selected_service['service'].lower() == "venue":
                    # Get venue type for venue searches
                    venue_type = input("What type of venue are you looking for? (e.g., banquet hall, restaurant, resort): ")
                    
                    # Create inputs for venue search
                    venue_inputs = {
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget'],
                        "num_guests": details["num_guests"],
                        "venue_type": venue_type
                    }
                    
                    # Use venue search coordinator for venue searches
                    venue_crew = Crew(
                        agents=[venue_search_coordinator],
                        tasks=[venue_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    
                    try:
                        # Use a timeout mechanism for Windows
                        import threading
                        import time
                        
                        result = [None]
                        exception = [None]
                        completed = [False]
                        
                        def run_venue_search():
                            try:
                                result[0] = venue_crew.kickoff(inputs=venue_inputs)
                                completed[0] = True
                            except Exception as e:
                                exception[0] = e
                        
                        # Start the search in a thread
                        search_thread = threading.Thread(target=run_venue_search)
                        search_thread.daemon = True
                        search_thread.start()
                        
                        # Wait for timeout
                        timeout = 180  # 3 minutes
                        search_thread.join(timeout)
                        
                        if not completed[0]:
                            if search_thread.is_alive():
                                raise TimeoutError("Search operation timed out")
                            elif exception[0]:
                                raise exception[0]
                            else:
                                raise Exception("Search failed to complete")
                                
                        service_output = result[0]
                        service_results = extract_text_from_crew_output(service_output)
                        
                        # Check if the results contain valid data or error messages
                        if isinstance(service_results, str):
                            if any(msg in service_results.lower() for msg in ["error", "no venues found", "could not extract"]):
                                raise ValueError("No venues found")
                        elif isinstance(service_results, list) and len(service_results) == 0:
                            raise ValueError("Empty venue results")
                        elif isinstance(service_results, dict) and "error" in service_results:
                            raise ValueError(f"Search error: {service_results['error']}")
                            
                        # Try to parse as JSON if it's a string
                        if isinstance(service_results, str):
                            try:
                                json_results = json.loads(service_results)
                                if not json_results or len(json_results) == 0:
                                    raise ValueError("Empty venue results after parsing")
                                service_results = json_results
                            except json.JSONDecodeError:
                                # Keep as string if not valid JSON
                                pass
                        
                        # Display venue results
                        print(format_venues_for_display(service_results))
                        
                    except (TimeoutError, ValueError, Exception) as e:
                        error_message = str(e)
                        print(f"\n⚠️ We couldn't find venues matching your criteria at this time.")
                        print(f"Error: {error_message}")
                        print("\nPlease try again later or consider modifying your search parameters:")
                        print("- Try a different location or venue type")
                        print("- Adjust your budget")
                        print("- Modify the guest count")
                        continue  # Skip the provider selection and go back to service selection
                    
                else:
                    # Create inputs for vendor search
                    vendor_inputs = {
                        "service_type": selected_service['service'],
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget']
                    }
                    
                    # Use vendor service coordinator for vendor searches
                    vendor_crew = Crew(
                        agents=[vendor_service_coordinator],
                        tasks=[vendor_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    
                    try:
                        # Use a timeout mechanism for Windows
                        import threading
                        import time
                        
                        result = [None]
                        exception = [None]
                        completed = [False]
                        
                        def run_vendor_search():
                            try:
                                result[0] = vendor_crew.kickoff(inputs=vendor_inputs)
                                completed[0] = True
                            except Exception as e:
                                exception[0] = e
                        
                        # Start the search in a thread
                        search_thread = threading.Thread(target=run_vendor_search)
                        search_thread.daemon = True
                        search_thread.start()
                        
                        # Wait for timeout
                        timeout = 180  # 3 minutes
                        search_thread.join(timeout)
                        
                        if not completed[0]:
                            if search_thread.is_alive():
                                raise TimeoutError("Search operation timed out")
                            elif exception[0]:
                                raise exception[0]
                            else:
                                raise Exception("Search failed to complete")
                                
                        service_output = result[0]
                        service_results = extract_text_from_crew_output(service_output)
                        
                        # Check if the results contain valid data or error messages
                        if isinstance(service_results, str):
                            if any(msg in service_results.lower() for msg in ["error", "no vendors found", "could not extract"]):
                                raise ValueError(f"No {selected_service['service']} vendors found")
                        elif isinstance(service_results, list) and len(service_results) == 0:
                            raise ValueError("Empty vendor results")
                        elif isinstance(service_results, dict) and "error" in service_results:
                            raise ValueError(f"Search error: {service_results['error']}")
                            
                        # Try to parse as JSON if it's a string
                        if isinstance(service_results, str):
                            try:
                                json_results = json.loads(service_results)
                                if not json_results or len(json_results) == 0:
                                    raise ValueError("Empty vendor results after parsing")
                                service_results = json_results
                            except json.JSONDecodeError:
                                # Keep as string if not valid JSON
                                pass
                        
                        # Display vendor results
                        print(format_vendors_for_display(service_results))
                        
                    except (TimeoutError, ValueError, Exception) as e:
                        error_message = str(e)
                        print(f"\n⚠️ We couldn't find {selected_service['service']} vendors matching your criteria at this time.")
                        print(f"Error: {error_message}")
                        print("\nPlease try again later or consider modifying your search parameters:")
                        print(f"- Try a different {selected_service['service']} type")
                        print("- Try a different location")
                        print("- Adjust your budget")
                        continue  # Skip the provider selection and go back to service selection
                
                # Only proceed with provider selection if we have results
                try:
                    # Ask if user wants to select a service provider
                    select_provider = input("\nWould you like to select one of these options? (yes/no): ").lower()
                    
                    if select_provider == "yes":
                        provider_num = int(input("Enter the number of the option you'd like to select: "))
                        providers = service_results
                        if isinstance(providers, str):
                            providers = json.loads(providers)
                        
                        if 1 <= provider_num <= len(providers):
                            selected_provider = providers[provider_num-1]
                            print(f"\nYou've selected: {selected_provider.get('name', selected_provider.get('Name', 'Unknown'))}")
                            
                            contact = selected_provider.get('contact', selected_provider.get('Contact', 'Not available'))
                            print(f"Contact: {contact}")
                            
                            address = selected_provider.get('address', selected_provider.get('Address'))
                            if address:
                                print(f"Address: {address}")
                                
                            price_field = selected_provider.get('price', selected_provider.get('Price'))
                            if price_field:
                                print(f"Price: {price_field}")
                            
                            # Store selected provider in the service
                            selected_service['selected_provider'] = selected_provider
                        else:
                            print("Invalid selection number. No option was selected.")
                except Exception as e:
                    print(f"Could not process selection: {str(e)}")
            else:
                print("Invalid service number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Let's try again.")