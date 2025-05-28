from agents.airport_service.main_graph import build_airport_service_graph


if __name__ == "__main__":
    graph = build_airport_service_graph()
    graph_image = graph.compile().get_graph(xray=True).draw_mermaid_png()
    with open("main_graph.png", "wb") as f:
        f.write(graph_image)
