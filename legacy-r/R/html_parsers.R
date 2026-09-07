#' @importFrom rvest html_node html_text html_attr html_nodes
#' @importFrom stringr str_extract
#' @importFrom magrittr %>%

# Helper for robust text extraction
extract_text <- function(node, css_selector) {
  extracted_node <- node %>% rvest::html_node(css_selector)
  if (!is.null(extracted_node)) {
    return(rvest::html_text(extracted_node, trim = TRUE))
  } else {
    return(NA_character_)
  }
}

# Helper for robust attribute extraction from a child node
extract_attr_from_child <- function(node, css_selector, attribute) {
  extracted_node <- node %>% rvest::html_node(css_selector)
  if (!is.null(extracted_node)) {
    return(rvest::html_attr(extracted_node, attribute))
  } else {
    return(NA_character_)
  }
}

#' Parses a single SciELO search results HTML page.
#' @param html_page An `xml_document` object representing the parsed HTML page.
#' @param query_obj A 'scielo_query' object (used for abstract language preference).
#' @return A list of data frames, each representing an article.
#' @keywords internal
parse_scielo_page <- function(html_page, query_obj) {
  articles <- html_page %>% rvest::html_nodes(".item")
  if (length(articles) == 0) {
    return(list()) # Return empty list if no articles found on this page
  }
  
  page_results <- list()
  for (article in articles) {
    title <- extract_text(article, ".title")
    
    # --- CAMBIO AQUÍ para extraer todos los autores ---
    authors_nodes <- article %>% rvest::html_nodes(".authors a.author")
    if (length(authors_nodes) > 0) {
      # Extract text from all author nodes and collapse them into a single string
      authors <- paste(rvest::html_text(authors_nodes, trim = TRUE), collapse = "; ")
    } else {
      # Fallback to the parent node's text if individual authors are not found
      # This can happen if the structure changes or is different for some articles.
      authors <- extract_text(article, ".authors")
    }
    # --- FIN DEL CAMBIO ---
    
    doi <- extract_attr_from_child(article, ".DOIResults a", "href")
    
    year_nodes <- article %>% rvest::html_node(".source") %>% rvest::html_nodes("span")
    year <- if (!is.null(year_nodes)) {
      year_text <- paste(rvest::html_text(year_nodes, trim = TRUE), collapse = " ")
      stringr::str_extract(year_text, "\\b\\d{4}\\b")
    } else {
      NA_character_
    }
    
    # Extract ID directly from the 'article' node itself (not a child)
    article_id <- rvest::html_attr(article, "id")
    
    abstract_text <- NA_character_
    if (!is.na(article_id)) {
      # Try English abstract first
      abstract_id_en <- paste0(article_id, "_en")
      abstract_node <- html_page %>% rvest::html_node(sprintf("div#%s", abstract_id_en))
      
      if (is.null(abstract_node) && query_obj$lang != "en") {
        abstract_id_lang <- paste0(article_id, "_", query_obj$lang)
        abstract_node <- html_page %>% rvest::html_node(sprintf("div#%s", abstract_id_lang))
      }
      
      if (!is.null(abstract_node)) {
        abstract_text <- rvest::html_text(abstract_node, trim = TRUE)
      }
    }
    
    page_results[[length(page_results) + 1]] <- data.frame(
      title = title,
      authors = authors,
      year = year,
      doi = doi,
      abstract = abstract_text,
      stringsAsFactors = FALSE
    )
  }
  return(page_results)
}