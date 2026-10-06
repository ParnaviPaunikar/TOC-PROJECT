import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import time

# ============================================================
# PAGE SETUP
# ============================================================
st.set_page_config(
    page_title="Useless Productions Eliminator",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 Useless Productions Eliminator")
st.caption("Interactive CFG Cleaning • Generating + Reachability Analysis • Algorithm Simulator")

# ============================================================
# HELPERS
# ============================================================
def parse_cfg(text):
    """Read CFG rules and return an ordered dictionary-like list."""
    rules = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "->" in line:
            left, right = line.split("->", 1)
        elif "→" in line:
            left, right = line.split("→", 1)
        else:
            continue

        left = left.strip()
        right = right.strip()

        if not left:
            continue

        alternatives = [x.strip() for x in right.split("|")]
        alternatives = [x for x in alternatives if x]

        if alternatives:
            rules.append((left, alternatives))

    return rules


def production_map(rules):
    result = {}
    for left, alternatives in rules:
        result.setdefault(left, [])
        result[left].extend(alternatives)
    return result


def get_variables(rules):
    return [left for left, _ in rules]


def get_terminals(rules, variables):
    terminals = []
    variable_set = set(variables)

    for _, alternatives in rules:
        for rhs in alternatives:
            if rhs == "ε":
                continue

            for ch in rhs:
                if ch.islower() or ch in "0123456789":
                    if ch not in terminals:
                        terminals.append(ch)

    # Symbols that are not LHS variables and are not uppercase variables
    # are also treated as terminals when they appear as standalone symbols.
    for _, alternatives in rules:
        for rhs in alternatives:
            for ch in rhs:
                if ch not in variable_set and ch not in terminals:
                    if ch.isalpha() and not ch.isupper():
                        terminals.append(ch)

    return terminals


def variable_symbols(rhs, variables):
    """Return variable symbols occurring in RHS."""
    variable_set = set(variables)
    found = []

    # Most student CFGs use single-letter variables.
    for ch in rhs:
        if ch in variable_set and ch not in found:
            found.append(ch)

    return found


def compute_generating(rules, variables):
    """Fixed-point computation of generating variables."""
    pmap = production_map(rules)
    generating = set()
    rounds = []

    changed = True

    while changed:
        changed = False
        round_info = []

        for variable in variables:
            if variable in generating:
                continue

            for rhs in pmap.get(variable, []):
                if rhs == "ε":
                    generating.add(variable)
                    changed = True
                    round_info.append(
                        f"{variable} → ε  ✓  {variable} is GENERATING"
                    )
                    break

                refs = variable_symbols(rhs, variables)

                if all(v in generating for v in refs):
                    generating.add(variable)
                    changed = True
                    round_info.append(
                        f"{variable} → {rhs}  ✓  all variables are generating"
                    )
                    break

        if round_info:
            rounds.append(round_info)

    return generating, rounds


def dependency_graph(rules, variables):
    graph = nx.DiGraph()
    graph.add_nodes_from(variables)

    for left, alternatives in rules:
        for rhs in alternatives:
            for v in variable_symbols(rhs, variables):
                graph.add_edge(left, v)

    return graph


def dfs_steps(graph, start):
    """Return DFS order and step-by-step path information."""
    visited = set()
    order = []
    steps = []

    def dfs(node):
        visited.add(node)
        order.append(node)
        steps.append({
            "node": node,
            "visited": order.copy(),
            "path": order.copy()
        })

        for nxt in graph.successors(node):
            if nxt not in visited:
                dfs(nxt)

    if start in graph:
        dfs(start)

    return order, steps


def reachable_from(rules, variables, start):
    graph = dependency_graph(rules, variables)
    order, steps = dfs_steps(graph, start)
    return set(order), steps, graph


def is_rule_clean(left, rhs, useful, variables):
    if left not in useful:
        return False

    for v in variable_symbols(rhs, variables):
        if v not in useful:
            return False

    return True


def format_rule(left, alternatives):
    return f"{left} → " + " | ".join(alternatives)


def draw_graph(graph, variables, generating, reachable, useful,
               active_node=None, active_edge=None, title="Dependency Graph"):
    fig, ax = plt.subplots(figsize=(10, 5))

    if len(graph.nodes) == 0:
        ax.text(0.5, 0.5, "No variables", ha="center", va="center")
        ax.axis("off")
        return fig

    pos = nx.spring_layout(graph, seed=42)

    node_sizes = []
    for node in graph.nodes:
        node_sizes.append(1500)

    node_labels = {n: n for n in graph.nodes}

    node_colors = []
    for node in graph.nodes:
        if node == active_node:
            node_colors.append("gold")
        elif node in useful:
            node_colors.append("lightgreen")
        elif node in generating and node not in reachable:
            node_colors.append("orange")
        elif node not in generating:
            node_colors.append("lightcoral")
        else:
            node_colors.append("lightblue")

    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="black",
        linewidths=1.5,
        ax=ax
    )

    normal_edges = []
    active_edges = []

    for edge in graph.edges:
        if active_edge is not None and edge == active_edge:
            active_edges.append(edge)
        else:
            normal_edges.append(edge)

    if normal_edges:
        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=normal_edges,
            arrows=True,
            arrowsize=20,
            width=1.5,
            ax=ax,
            connectionstyle="arc3,rad=0.05"
        )

    if active_edges:
        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=active_edges,
            arrows=True,
            arrowsize=25,
            width=4,
            edge_color="red",
            ax=ax,
            connectionstyle="arc3,rad=0.05"
        )

    nx.draw_networkx_labels(
        graph,
        pos,
        labels=node_labels,
        font_size=14,
        font_weight="bold",
        ax=ax
    )

    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.axis("off")

    return fig


def show_cfg_box(title, rules, removed=None):
    st.markdown(f"### {title}")

    if not rules:
        st.info("No productions.")
        return

    for left, alternatives in rules:
        st.code(format_rule(left, alternatives), language="text")

    if removed:
        st.markdown("**Removed productions:**")
        for item in removed:
            st.write(item)


# ============================================================
# INPUT
# ============================================================
st.sidebar.header("⚙️ CFG Input")

default_cfg = """S -> AB | a
A -> a
B -> b
C -> cC
D -> d"""

cfg_text = st.sidebar.text_area(
    "Enter your Context-Free Grammar:",
    value=default_cfg,
    height=220
)

start_symbol = st.sidebar.text_input(
    "Start Symbol:",
    value="S",
    max_chars=10
).strip()

speed = st.sidebar.slider(
    "Animation Speed",
    min_value=0.05,
    max_value=1.0,
    value=0.25,
    step=0.05
)

run_analysis = st.sidebar.button(
    "🔍 ANALYZE CFG",
    use_container_width=True
)

st.sidebar.markdown("---")
st.sidebar.info(
    "Tip: Use uppercase letters for variables and lowercase letters "
    "for terminals. Example: S -> AB | a"
)

# ============================================================
# MAIN ANALYSIS
# ============================================================
if run_analysis:
    rules = parse_cfg(cfg_text)

    if not rules:
        st.error("❌ No valid productions found.")
        st.stop()

    variables = get_variables(rules)

    # Preserve order while removing duplicates
    variables = list(dict.fromkeys(variables))

    if start_symbol not in variables:
        st.error(
            f"❌ Start symbol '{start_symbol}' is not present on the left-hand side."
        )
        st.stop()

    terminals = get_terminals(rules, variables)
    pmap = production_map(rules)

    generating, generating_rounds = compute_generating(rules, variables)
    reachable, dfs_info, graph = reachable_from(
        rules, variables, start_symbol
    )
    useful = generating.intersection(reachable)

    non_generating = set(variables) - generating
    unreachable = set(variables) - reachable
    useless = set(variables) - useful

    # --------------------------------------------------------
    # TOP PIPELINE
    # --------------------------------------------------------
    st.markdown("## 🧠 Algorithm Simulator")

    pipeline = [
        "1️⃣ INPUT CFG",
        "2️⃣ SCANNING",
        "3️⃣ GENERATING TEST",
        "4️⃣ DFS TRAVERSAL",
        "5️⃣ USELESS CHECK",
        "6️⃣ REMOVING",
        "7️⃣ CLEAN CFG"
    ]

    cols = st.columns(len(pipeline))
    for col, item in zip(cols, pipeline):
        col.markdown(
            f"<div style='text-align:center;font-weight:bold'>{item}</div>",
            unsafe_allow_html=True
        )

    st.divider()

    # --------------------------------------------------------
    # STEP 1: INPUT CFG
    # --------------------------------------------------------
    st.markdown("## 🟦 Step 1 — Input CFG")

    input_placeholder = st.empty()

    for i, (left, alternatives) in enumerate(rules):
        current = rules[:i + 1]

        with input_placeholder.container():
            st.success(f"📥 Reading production {i + 1} of {len(rules)}")
            for l, alts in current:
                st.code(format_rule(l, alts), language="text")

        time.sleep(speed)

    st.success("✅ CFG input scanned successfully.")

    # --------------------------------------------------------
    # STEP 2: VARIABLES AND TERMINALS
    # --------------------------------------------------------
    st.markdown("## 🟩 Step 2 — Scanning Variables and Terminals")

    var_box = st.empty()

    discovered_vars = []
    for v in variables:
        discovered_vars.append(v)

        with var_box.container():
            st.markdown("**Variables discovered:**")
            st.write(" → ".join(discovered_vars))

        time.sleep(speed)

    term_box = st.empty()
    discovered_terms = []

    for t in terminals:
        discovered_terms.append(t)

        with term_box.container():
            st.markdown("**Terminals discovered:**")
            st.write(" → ".join(discovered_terms))

        time.sleep(speed)

    if not terminals:
        term_box.info("No explicit lowercase terminals detected.")

    # --------------------------------------------------------
    # STEP 3: GENERATING ANALYSIS
    # --------------------------------------------------------
    st.markdown("## 🟨 Step 3 — Generating Variable Analysis")

    st.write(
        "A variable is generating if it can eventually produce only terminals "
        "or ε."
    )

    gen_status = {v: False for v in variables}
    generation_box = st.empty()

    for round_no, round_items in enumerate(generating_rounds, start=1):
        for item in round_items:
            variable = item.split(" → ")[0].strip()

            if variable in gen_status:
                gen_status[variable] = True

            with generation_box.container():
                st.markdown(f"### 🔍 Generating Round {round_no}")

                for v in variables:
                    if gen_status[v]:
                        st.success(f"{v}  →  GENERATING ✓")
                    else:
                        st.warning(f"{v}  →  Not known yet")

                st.info(item)

            time.sleep(speed)

    with generation_box.container():
        st.markdown("### ✅ Final Generating Result")
        for v in variables:
            if v in generating:
                st.success(f"{v} → GENERATING ✓")
            else:
                st.error(f"{v} → NON-GENERATING ✗")

    # --------------------------------------------------------
    # PRODUCTION-BY-PRODUCTION GENERATING EXPLANATION
    # --------------------------------------------------------
    st.markdown("### 🔎 Production-by-Production Check")

    production_box = st.empty()
    known = set()

    # Display an understandable simulation of repeated fixed-point checking.
    for pass_no in range(1, len(variables) + 2):
        changed = False

        for left, alternatives in rules:
            for rhs in alternatives:
                refs = variable_symbols(rhs, variables)

                if rhs == "ε":
                    result = True
                else:
                    result = all(v in known for v in refs)

                if result and left not in known:
                    known.add(left)
                    changed = True

                status_lines = []

                if not refs:
                    status_lines.append("Only terminal symbols → can generate ✓")
                else:
                    for v in refs:
                        if v in known:
                            status_lines.append(f"{v} ✓ generating")
                        else:
                            status_lines.append(f"{v} ✗ not known")

                with production_box.container():
                    st.markdown(f"**Pass {pass_no} — Checking:** `{left} → {rhs}`")
                    for line in status_lines:
                        st.write(line)

                    if result:
                        st.success(f"RESULT: {left} is GENERATING 🟢")
                    else:
                        st.warning(f"RESULT: {left} cannot be marked yet 🟡")

                time.sleep(speed)

        if not changed:
            break

    # --------------------------------------------------------
    # STEP 4: DEPENDENCY GRAPH
    # --------------------------------------------------------
    st.markdown("## 🟪 Step 4 — Animated Dependency Graph")

    st.write(
        "Each directed edge A → B means production A contains variable B."
    )

    graph_box = st.empty()

    graph_nodes = list(graph.nodes)
    partial_graph = nx.DiGraph()

    # Add nodes one by one
    for node in graph_nodes:
        partial_graph.add_node(node)

        fig = draw_graph(
            partial_graph,
            variables,
            generating,
            reachable,
            useful,
            active_node=node,
            title=f"Adding Variable Node: {node}"
        )

        with graph_box.container():
            st.pyplot(fig, clear_figure=True)
            st.info(f"🟡 Adding node: {node}")

        plt.close(fig)
        time.sleep(speed)

    # Add edges one by one
    for source, target in graph.edges:
        partial_graph.add_edge(source, target)

        fig = draw_graph(
            partial_graph,
            variables,
            generating,
            reachable,
            useful,
            active_node=target,
            active_edge=(source, target),
            title=f"Adding Dependency: {source} → {target}"
        )

        with graph_box.container():
            st.pyplot(fig, clear_figure=True)
            st.info(f"➡️ Dependency detected: {source} → {target}")

        plt.close(fig)
        time.sleep(speed)

    fig = draw_graph(
        graph,
        variables,
        generating,
        reachable,
        useful,
        title="Complete Dependency Graph"
    )

    graph_box.pyplot(fig, clear_figure=True)
    plt.close(fig)

    # --------------------------------------------------------
    # STEP 5: DFS REACHABILITY
    # --------------------------------------------------------
    st.markdown("## 🟥 Step 5 — DFS Reachability Traversal")

    st.write(
        f"DFS starts from the start symbol **{start_symbol}**."
    )

    dfs_box = st.empty()

    visited_so_far = []

    for step_no, step in enumerate(dfs_info, start=1):
        current = step["node"]
        visited_so_far = step["visited"]

        active_edge = None

        if len(visited_so_far) >= 2:
            active_edge = (
                visited_so_far[-2],
                visited_so_far[-1]
            )

        fig = draw_graph(
            graph,
            variables,
            generating,
            reachable,
            useful,
            active_node=current,
            active_edge=active_edge,
            title=f"DFS Step {step_no}: Visiting {current}"
        )

        with dfs_box.container():
            st.pyplot(fig, clear_figure=True)
            st.success(
                f"📍 Current node: {current}"
            )
            st.write(
                "DFS path: " + " → ".join(visited_so_far)
            )
            st.write(
                "Visited: " + ", ".join(visited_so_far)
            )

        plt.close(fig)
        time.sleep(speed)

    with dfs_box.container():
        st.success(
            "✅ DFS completed. Reachable variables: "
            + ", ".join(sorted(reachable))
        )

    # --------------------------------------------------------
    # STEP 6: USEFUL / USELESS
    # --------------------------------------------------------
    st.markdown("## 🟧 Step 6 — Useful / Useless Variable Check")

    st.write(
        "**Useful = Generating ∩ Reachable**"
    )

    useful_box = st.empty()

    for v in variables:
        if v in useful:
            message = f"🟢 {v}: GENERATING ✓ + REACHABLE ✓ → USEFUL"
            level = "success"
        elif v in non_generating:
            message = f"🔴 {v}: NON-GENERATING ✗ → USELESS"
            level = "error"
        elif v in unreachable:
            message = f"🟠 {v}: UNREACHABLE ✗ → USELESS"
            level = "warning"
        else:
            message = f"🟠 {v}: USELESS"

            level = "warning"

        with useful_box.container():
            st.markdown(f"### Checking `{v}`")

            if level == "success":
                st.success(message)
            elif level == "error":
                st.error(message)
            else:
                st.warning(message)

        time.sleep(speed)

    # --------------------------------------------------------
    # STEP 7: REMOVING USELESS PRODUCTIONS
    # --------------------------------------------------------
    st.markdown("## 🗑️ Step 7 — Removing Useless Productions")

    removed = []
    clean_rules = []

    removal_box = st.empty()

    for left, alternatives in rules:
        kept = []

        for rhs in alternatives:
            reason = None

            if left not in useful:
                if left in non_generating:
                    reason = "Non-generating LHS"
                elif left in unreachable:
                    reason = "Unreachable LHS"
                else:
                    reason = "Useless variable"
            elif not is_rule_clean(left, rhs, useful, variables):
                bad = [
                    v for v in variable_symbols(rhs, variables)
                    if v not in useful
                ]

                if bad:
                    reason = (
                        "Contains useless variable: "
                        + ", ".join(bad)
                    )
                else:
                    reason = "Contains a variable not retained"

            if reason:
                removed.append((left, rhs, reason))

                with removal_box.container():
                    st.error(
                        f"❌ Removing: {left} → {rhs}"
                    )
                    st.caption(f"Reason: {reason}")

                time.sleep(speed)
            else:
                kept.append(rhs)

                with removal_box.container():
                    st.success(
                        f"✅ Keeping: {left} → {rhs}"
                    )

                time.sleep(speed)

        if kept:
            clean_rules.append((left, kept))

    if not removed:
        removal_box.success(
            "No useless productions needed to be removed."
        )

    # --------------------------------------------------------
    # BEFORE / AFTER TRANSFORMATION
    # --------------------------------------------------------
    st.markdown("## 🔄 Before → Cleaning → After")

    before_col, middle_col, after_col = st.columns([1, 0.35, 1])

    with before_col:
        st.markdown("### 🔴 Original CFG")
        for left, alternatives in rules:
            st.code(format_rule(left, alternatives), language="text")

    with middle_col:
        st.markdown("### 🧹")
        st.markdown(
            "<div style='font-size:45px;text-align:center'>→</div>",
            unsafe_allow_html=True
        )
        st.caption("Remove useless productions")

    with after_col:
        st.markdown("### 🟢 Clean CFG")

        if clean_rules:
            for left, alternatives in clean_rules:
                st.code(format_rule(left, alternatives), language="text")
        else:
            st.warning("No useful productions remain.")

    # --------------------------------------------------------
    # CLEAN CFG ANIMATION
    # --------------------------------------------------------
    st.markdown("## ✨ Animated Clean CFG Construction")

    clean_box = st.empty()
    built = []

    for rule in clean_rules:
        built.append(rule)

        with clean_box.container():
            st.markdown("### Building clean grammar...")
            for left, alternatives in built:
                st.success(format_rule(left, alternatives))

        time.sleep(speed)

    # --------------------------------------------------------
    # GRAMMAR MATRIX
    # --------------------------------------------------------
    st.markdown("## 📊 Grammar Analysis Matrix")

    matrix_box = st.empty()

    matrix_rows = []

    for v in variables:
        if v in generating:
            gen_text = "YES ✓"
        else:
            gen_text = "NO ✗"

        if v in reachable:
            reach_text = "YES ✓"
        else:
            reach_text = "NO ✗"

        if v in useful:
            useful_text = "YES ✓"
            decision = "KEEP"
        else:
            useful_text = "NO ✗"
            decision = "REMOVE"

        matrix_rows.append({
            "Variable": v,
            "Production": " | ".join(pmap.get(v, [])),
            "Generating": gen_text,
            "Reachable": reach_text,
            "Useful": useful_text,
            "Decision": decision
        })

        with matrix_box.container():
            st.table(matrix_rows)

        time.sleep(speed)

    # --------------------------------------------------------
    # REMOVED PRODUCTION TABLE
    # --------------------------------------------------------
    st.markdown("## 🧾 Removed Productions")

    if removed:
        for left, rhs, reason in removed:
            st.error(
                f"`{left} → {rhs}`  —  {reason}"
            )
    else:
        st.success("No productions removed.")

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------
    st.markdown("## 🏁 Final Result")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Original Variables",
        len(variables)
    )

    c2.metric(
        "Generating",
        len(generating)
    )

    c3.metric(
        "Reachable",
        len(reachable)
    )

    c4.metric(
        "Useful",
        len(useful)
    )

    st.divider()

    st.markdown("### Variable Classification")

    class_cols = st.columns(3)

    with class_cols[0]:
        st.markdown("#### 🟢 Useful")
        if useful:
            st.success(", ".join(sorted(useful)))
        else:
            st.info("None")

    with class_cols[1]:
        st.markdown("#### 🔴 Non-Generating")
        if non_generating:
            st.error(", ".join(sorted(non_generating)))
        else:
            st.success("None")

    with class_cols[2]:
        st.markdown("#### 🟠 Unreachable")
        if unreachable:
            st.warning(", ".join(sorted(unreachable)))
        else:
            st.success("None")

    st.markdown("### 🧹 Final Clean Grammar")

    if clean_rules:
        for left, alternatives in clean_rules:
            st.success(format_rule(left, alternatives))
    else:
        st.error("No clean grammar could be produced.")

    st.markdown(
        """
        ### 🎓 Algorithm Complete

        **Generating Analysis → Dependency Graph → DFS Reachability
        → Useful Variables → Useless Production Removal → Clean CFG**

        The cleaned grammar contains only useful variables and productions.
        """
    )

else:
    # ========================================================
    # WELCOME SCREEN
    # ========================================================
    st.markdown("## 👋 Welcome!")

    st.write(
        "Enter a Context-Free Grammar in the sidebar and click "
        "**ANALYZE CFG** to start the animated algorithm simulator."
    )

    st.markdown("### Example Input")

    st.code(
        """S -> AB | a
A -> a
B -> b
C -> cC
D -> d""",
        language="text"
    )

    st.markdown("### What the simulator shows")

    info_cols = st.columns(4)

    with info_cols[0]:
        st.info("🔎 CFG scanning")

    with info_cols[1]:
        st.success("🟢 Generating analysis")

    with info_cols[2]:
        st.warning("🧭 DFS reachability")

    with info_cols[3]:
        st.error("🗑️ Useless removal")

    st.markdown("### Animation Flow")

    st.markdown(
        """
        **INPUT CFG**
        ↓
        **SCAN VARIABLES / TERMINALS**
        ↓
        **CHECK GENERATING VARIABLES**
        ↓
        **BUILD DEPENDENCY GRAPH**
        ↓
        **DFS FROM START SYMBOL**
        ↓
        **FIND USEFUL VARIABLES**
        ↓
        **REMOVE USELESS PRODUCTIONS**
        ↓
        **GENERATE CLEAN CFG**
        """
    )

    st.caption(
        "Tip: Keep the browser tab open while the animation is running."
    )
