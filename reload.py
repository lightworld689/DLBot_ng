def hotreload(new_code_file: str) -> int:
    """
    Reloads and executes code from the specified file.

    Parameters:
    - new_code_file (str): Path to the file containing the new code.

    Returns:
    - int: 0 if the code was executed successfully, -1 if there was an error.
    """
    try:
        # Open and read the new code file
        with open(new_code_file, 'r') as code_file:
            code = code_file.read()
        
        # Execute the code
        exec(code, globals())
        return 0
    except Exception as e:
        # Optionally log the exception message for debugging
        print(f"Error executing code from file {new_code_file}: {e}")
        return -1

