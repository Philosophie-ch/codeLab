#!/usr/bin/env bash

case "${1}" in
    "" | "-h" | "--help")
        echo "Usage: ${0} <file_1> <file_2> ..."
        echo "WARNING: Modifies the file in-place using `sed` and the replacement table hardcoded in this script. You should backup your files before using this script."
        exit 0
        ;;

    "-d" | "--dry-run" | "--debug" | "--dry")
        shift 1
        dry_run=true
        ;;
esac


function replace_string() {

    if [ -z "${1}" ] || [ -z "${2}" ] || [ -z "${3}" ]; then
        echo "Missing arguments. Three needed:"
        echo "replace_string <from> <to> <file>"
        return 1
    fi

    if [ "$dry_run" = true ]; then
        echo "sed -i \"s/${1}/${2}/g\" \"${3}\""
        return
    fi

    sed -i "s/${1}/${2}/g" "${3}"
}


# Array of arrays to replace en masse
declare -A replace_map
replace_map=(

    ['Bruno, G.Anthony']='Bruno, G.~Anthony'
    ['Bjelke, J.Fr.']='Bjelke, J~.Fr.'
    ['Byles, W.Esdaile']='Byles, W.~Esdaile'
    ['Cunningham, G.Watts']='Cunningham, G~.Watts'
    ['Diamond, Wm.Craig']='Diamond, Wm.~Craig'
    ['Fischer, H.Ernst']='Fischer, H.~Ernst'
    ['Finlay-Freundlich, E.']='Finlay-Freundlich, Erwin'
    ['s {\\em Sala delle Asse']='s {\\em Sala delle Asse}'
    ['Hindley, J.Roger']='Hindley, J.~Roger'
    ['Kane, G.Stanley']='Kane, G.~Stanley'
    ['McDermott, A.Charlene']='McDermott, A.~Charlene'
    ['Mercken, H.Paul']='Mercken, H.~Paul'
    ['Rasmussen, M.E.Tranekjaer']='Rasmussen, M.E.~Tranekjaer'
    ['Stebbing, L.Susan']='Stebbing, L.~Susan'
    ['Stirling, J.Hutchison']='Stirling, J.~Hutchison'
    ['Tracz, R.Brian']='Tracz, R.~Brian'
    ['Vidal, J.Z.Antonio']='Vidal, J.Z~.Antonio'
    ['Wilson, W.Kent']='Wilson, W.~Kent'
    ['Willard, M.B']='Willard, Mary Beth'
    ['Societ{\\{\\`a}} italiana di logica e filosofia della scienza']='Societ{\\`a} italiana di logica e filosofia della scienza'
    ['schwabe-blanke:2008']='schwabe_l-blanke:2008'
    ['ë']='{\\"e}'
    ['ä']='{\\"a}'
    ['ö']='{\\"o}'
    ['ü']='{\\"u}'
    ['Ä']='{\\"A}'
    ['Ö']='{\\"O}'
    ['Ü']='{\\"U)'
    ['fabian:1985']='fabian_r:1985'
    ['findler-meltzer:1971']='findler_nv-meltzer:1971'
    ['findler:1979']='findler_nv:1979'
    ['grim-etal:1998']='grim_p-etal:1998'
    ['hartshorne-reese:1953']='hartshorne_r-reese:1953'
    ['henrich:1992']='henrich_d:1992'
    ['henrich:1992a']='henrich_d:1992a'
    ['henrich:1996']='henrich_d:1996'
    ['henrich:1983']='henrich_d:1983'
    ['henrich:1979']='henrich_d:1979'
    ['henrich:1977']='henrich_d:1977'
    ['henrich-etal:1960']='henrich_d-etal:1960'
    ['henrich-horstmann:1982']='henrich_d-horstmann:1982'
    ['henrich-horstmann:1988']='henrich_d-horstmann:1988'
    ['henrich-jamme:1986']='henrich_d-jamme:1986'
    ['henrich-wagner:1966']='henrich_d-wagner:1966'
    ['hyden:1969']='hyden_h:1969'
    ['kearn_m-etal:1989']='kaern_m-etal:1989'
    ['keyt-miller_f:1991']='keyt-miller:1991'
    ['landman-veltman:1984']='landman_f-veltman:1984'
    ['macnish-etal:1994']='macnish_c-etal:1994'
    ['pont-etal:2007']='pont_jc-etal:2007'
    ['pont-padovani:2006']='pont_jc-padovani:2006'
    ['pont-padovani:2007']='pont_jc-padovani:2007'
    ['radman:1995']='radman_z:1995'
    ['radman:2012']='radman_z:2012'
    ['radman:2013']='radman_z:2013'
    ['sammut-etal:2013']='sammut_g-etal:2013'
    ['sankey:1999']='sankey_h:1999'
    ['santoro-gorrie:2005']='santoro_ma-gorrie:2005'
    ['schear:2013']='schear_jk:2013'
    ['seldin_j-hindley:1980']='seldin_jp-hindley:1980'
    ['tasoulias:1997']='tasioulas:1997'
    ['endler::1993']='endler:1993'
    ['gauthier_i-tarr;2002']='gauthier_i-tarr:2002'
    ['winch:1969']='winch_p:1969'
    ['woody-etal:2012']='woody_a-etal:2012'



    # Examples:
    #["𝑋"]="X"
    #["𝑌"]="Y"
    #["𝑍"]="Z"
    #["𝜆"]="λ"
    #["𝑅"]="R"
    #["“"]="\""
    #["”"]="\""
    #["’"]="'"
    #["‘"]="'"
    #["X1"]="X₁"
    #["X2"]="X₂"
    #["X3"]="X₃"
    #["_0"]="₀"
    #["_1"]="₁"
    #["_2"]="₂"
    #["_3"]="₃"
    # Patterns
    # md emphasis to LaTeX emphasis
    #["\*\([^*]*\)\*"]='\\emph{\1}'
)


for file in "${@}"; do
    # Loop through the array and replace the strings
    for from in "${!replace_map[@]}"; do
        to="${replace_map[${from}]}"

        replace_string "${from}" "${to}" "${file}"

    done
done
