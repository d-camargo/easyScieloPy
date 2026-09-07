# fetch_scielo_results.R

# Tell R CMD check that `.` is a known variable
utils::globalVariables(".")

#' Fetch search results from SciELO
#'
#' This is the core function that performs the web scraping and data extraction.
#' It handles pagination and combines results into a single data frame.
#'
#' @param query_obj A `scielo_query` object.
#' @return A `data.frame` containing all fetched articles.
#'
#' @importFrom httr GET status_code add_headers
#' @importFrom xml2 read_html
#' @importFrom dplyr bind_rows
#' @importFrom magrittr %>%
#' @importFrom stats runif
#' @export
fetch_scielo_results <- function(query_obj) {
  required_packages <- c("httr", "xml2", "rvest", "dplyr", "stringr")
  missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
  if (length(missing_packages) > 0) {
    stop(paste0("Missing required packages: ", paste(missing_packages, collapse = ", "), "."), call. = FALSE)
  }
  
  results_list <- list()
  total_articles_fetched <- 0
  current_from_idx <- 1
  items_per_page <- 15
  effective_n_max <- query_obj$n_max
  
  # Only reliable desktop User-Agents
  user_agents <- c(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
  )
  
  build_headers <- function() {
    c(
      "User-Agent" = sample(user_agents, 1),
      "Accept-Language" = "en-US,en;q=0.9",
      "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Connection" = "keep-alive"
    )
  }
  
  # Determine total hits
  if (is.null(effective_n_max)) {
    initial_url <- build_scielo_url(query_obj, 1, items_per_page)
    initial_resp <- tryCatch({
      httr::GET(initial_url, httr::add_headers(.headers = build_headers()))
    }, error = function(e) {
      stop("Initial connection failed: ", e$message, call. = FALSE)
    })
    
    if (httr::status_code(initial_resp) == 403) {
      stop("Access denied with HTTP 403. SciELO may be blocking automated requests. Try slowing down or rotating headers.", call. = FALSE)
    }
    
    if (httr::status_code(initial_resp) != 200) {
      stop("Initial fetch failed. Status: ", httr::status_code(initial_resp), call. = FALSE)
    }
    
    initial_page_html <- xml2::read_html(initial_resp)
    total_hits_node <- initial_page_html %>% rvest::html_node("#TotalHits")
    if (!is.null(total_hits_node)) {
      total_hits <- total_hits_node %>%
        rvest::html_text(trim = TRUE) %>%
        gsub("\\D", "", .) %>%
        as.integer()
      effective_n_max <- total_hits
    } else {
      warning("Could not determine total hits. Defaulting to 100.", call. = FALSE)
      effective_n_max <- 100
    }
  }
  
  # Pagination loop
  while (total_articles_fetched < effective_n_max) {
    Sys.sleep(runif(1, 3.0, 6.0))  # Slightly wider random delay
    
    current_url <- build_scielo_url(query_obj, current_from_idx, items_per_page)
    
    resp <- tryCatch({
      httr::GET(current_url, httr::add_headers(.headers = build_headers()))
    }, error = function(e) {
      warning("Request failed at index ", current_from_idx, ": ", e$message)
      return(NULL)
    })
    
    if (is.null(resp)) break
    
    if (httr::status_code(resp) == 403) {
      warning("Access denied at index ", current_from_idx, ". Try changing User-Agent.", call. = FALSE)
      break
    }
    
    if (httr::status_code(resp) != 200) {
      warning("HTTP error at index ", current_from_idx, ": ", httr::status_code(resp))
      break
    }
    
    page_html <- xml2::read_html(resp)
    articles <- parse_scielo_page(page_html, query_obj)
    
    # Fallback: retry if empty
    if (length(articles) == 0) {
      warning("No articles found on page. Retrying with a different User-Agent...")
      resp_retry <- tryCatch({
        httr::GET(current_url, httr::add_headers(.headers = build_headers()))
      }, error = function(e) {
        warning("Retry failed: ", e$message)
        return(NULL)
      })
      
      if (!is.null(resp_retry) && httr::status_code(resp_retry) == 200) {
        page_html_retry <- xml2::read_html(resp_retry)
        articles <- parse_scielo_page(page_html_retry, query_obj)
      }
    }
    
    if (length(articles) == 0) {
      if (total_articles_fetched == 0) message("No articles found.")
      break
    }
    
    for (article_df in articles) {
      if (total_articles_fetched < effective_n_max) {
        results_list[[length(results_list) + 1]] <- article_df
        total_articles_fetched <- total_articles_fetched + 1
      } else {
        break
      }
    }
    
    current_from_idx <- current_from_idx + items_per_page
  }
  
  if (length(results_list) == 0) {
    return(data.frame(title=character(), authors=character(), year=character(), doi=character(), abstract=character(), stringsAsFactors = FALSE))
  }
  
  dplyr::bind_rows(results_list)
}
