import boto3

# Configuración de la sesión
session = boto3.Session(profile_name="projecte1")
agent_client = session.client("bedrock-agent-runtime", region_name="us-east-1")

# Reemplaza con tus datos reales
agent_id = "BEBBVC6EFW"
agent_alias_id = "TSTALIASID"  # Alias ID REAL y READY
session_id = "session001"      # Mantener historial opcional

print("💬 Chat con tu Agente (escribe 'exit' para salir)\n")

while True:
    user_input = input("Tú: ")
    
    if user_input.lower() in ["exit", "quit", "salir"]:
        print("👋 Terminando chat.")
        break

    try:
        # Invocar agente
        response = agent_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=user_input
        )

        # Leer la respuesta en streaming
        print("Agente:", end=" ")
        for event in response.get("completion", []):
            if "chunk" in event and "bytes" in event["chunk"]:
                print(event["chunk"]["bytes"].decode("utf-8"), end="")
        print("\n")

    except Exception as e:
        print(f"❌ Error al invocar el agente: {e}")
