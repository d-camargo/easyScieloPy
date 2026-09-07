#' Normalize SciELO collection names or ISO codes
#'
#' Converts country names or ISO codes into valid SciELO collection codes.
#' Only one value is allowed.
#'
#' @param collections A character vector of length 1: a country name (e.g., "Costa Rica")
#' or a valid SciELO ISO code (e.g., "cri").
#'
#' @return A character string representing the normalized SciELO collection code.
#' @export
#'
#' @examples
#' normalize_collections("Costa Rica")  # returns "cri"
#' normalize_collections("cri")         # returns "cri"
#'
normalize_collections <- function(collections) {
  country_to_code <- c(
    "Costa Rica" = "cri", "M\u00e9xico" = "mex", "Brasil" = "bra", "Colombia" = "col",
    "Argentina" = "arg", "Chile" = "chl", "Cuba" = "cub", "Per\u00fa" = "per",
    "Venezuela" = "ven", "Uruguay" = "ury", "Ecuador" = "ecu",
    "Paraguay" = "pry", "Panam\u00e1" = "pan"
  )
  
  allowed_codes <- unname(country_to_code)
  
  # ---- Validations ----
  if (!is.character(collections)) {
    stop("'collections' must be a character vector.", call. = FALSE)
  }
  
  if (length(collections) != 1) {
    stop("Only one collection is allowed at a time. Please provide a single country name or ISO code.", call. = FALSE)
  }
  
  value <- trimws(collections[[1]])
  
  if (nchar(value) < 2) {
    stop("The provided collection value is too short to be valid.", call. = FALSE)
  }
  
  normalize <- function(x) tolower(iconv(x, to = "ASCII//TRANSLIT"))
  
  # ---- Direct match (code) ----
  if (tolower(value) %in% allowed_codes) {
    return(tolower(value))
  }
  
  # ---- Name match ----
  matched_index <- match(normalize(value), normalize(names(country_to_code)))
  
  if (!is.na(matched_index)) {
    return(unname(country_to_code[matched_index]))
  }
  
  # ---- Invalid value ----
  stop(paste0(
    "Invalid collection: '", value, "'. Please use a valid country name or ISO code. ",
    "Valid values include: ", paste(names(country_to_code), collapse = ", "), "."
  ), call. = FALSE)
}
